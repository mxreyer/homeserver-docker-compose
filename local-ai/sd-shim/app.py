"""
Minimal OpenAI-images-compatible HTTP shim around sd-cli.

sd-cli fully loads and releases every model on each invocation (see
`model manager releasing params backend buffer` in its logs), which is
the whole point of using it here instead of the always-resident sd-server:
zero idle RAM/VRAM between generations, at the cost of a slow (~80s) cold
start on every single request. That tradeoff was chosen deliberately for
this box's 16GB unified memory budget, shared with Ollama.

Only stdlib is used on purpose, to keep the runtime image minimal.
"""

import base64
import json
import os
import shlex
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SD_CLI = os.environ.get("SD_CLI", "/sd.cpp/bin/sd-cli")
DIFFUSION_MODEL = os.environ["DIFFUSION_MODEL"]
VAE = os.environ["VAE"]
LLM = os.environ["LLM"]
BACKEND = os.environ.get("BACKEND", "te=cpu,vae=cpu,diffusion=vulkan0")
CFG_SCALE = os.environ.get("CFG_SCALE", "1.0")
STEPS = os.environ.get("STEPS", "4")
EXTRA_ARGS = shlex.split(os.environ.get("EXTRA_ARGS", "--diffusion-fa --vae-tiling"))
GEN_TIMEOUT = int(os.environ.get("GEN_TIMEOUT", "600"))
TERM_GRACE = int(os.environ.get("TERM_GRACE", "15"))
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
MODEL_ID = os.path.basename(DIFFUSION_MODEL)

# Only one sd-cli process may touch the GPU at a time -- this is the same
# memory ceiling that caused the original crash, so requests are serialized
# rather than run concurrently.
gen_lock = threading.Lock()


def unload_ollama_models():
    """Evict any resident Ollama model before touching the GPU ourselves.

    This isn't optional: when generation is triggered via chat tool-calling,
    the chat model is by definition loaded (it has to be, to decide to call
    the tool), so without this, Ollama and sd-cli always contend for the
    same unified memory pool on every single image request.
    """
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/ps", timeout=5) as resp:
            models = json.load(resp).get("models", [])
    except Exception as e:
        print(f"[sd-shim] could not query ollama /api/ps, skipping unload: {e}")
        return
    for m in models:
        name = m.get("name")
        try:
            req = urllib.request.Request(
                f"{OLLAMA_BASE_URL}/api/generate",
                data=json.dumps({"model": name, "keep_alive": 0}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=10).read()
            print(f"[sd-shim] unloaded ollama model: {name}")
        except Exception as e:
            print(f"[sd-shim] failed to unload ollama model {name}: {e}")
    if models:
        # Unload is asynchronous on ollama's side -- give VRAM a moment to
        # actually free before we start loading the diffusion model.
        for _ in range(10):
            try:
                with urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/ps", timeout=5) as resp:
                    if not json.load(resp).get("models", []):
                        break
            except Exception:
                break
            time.sleep(1)


def run_generation(prompt: str, width: int, height: int, seed: int) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "out.png")
        cmd = [
            SD_CLI,
            "--diffusion-model", DIFFUSION_MODEL,
            "--vae", VAE,
            "--llm", LLM,
            "-p", prompt,
            "--cfg-scale", CFG_SCALE,
            "--steps", STEPS,
            "-W", str(width),
            "-H", str(height),
            "-s", str(seed),
            "--backend", BACKEND,
            *EXTRA_ARGS,
            "-o", out_path,
        ]
        with gen_lock:
            unload_ollama_models()
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            try:
                stdout, stderr = proc.communicate(timeout=GEN_TIMEOUT)
            except subprocess.TimeoutExpired:
                # Killing a process mid-Vulkan-operation via SIGKILL can leave
                # the GPU/driver in a bad state for whatever runs next, so try
                # a graceful SIGTERM first and only escalate if it ignores it.
                print(f"[sd-shim] sd-cli exceeded {GEN_TIMEOUT}s, sending SIGTERM")
                proc.terminate()
                try:
                    stdout, stderr = proc.communicate(timeout=TERM_GRACE)
                except subprocess.TimeoutExpired:
                    print("[sd-shim] sd-cli ignored SIGTERM, sending SIGKILL")
                    proc.kill()
                    stdout, stderr = proc.communicate()
                raise RuntimeError(f"sd-cli timed out after {GEN_TIMEOUT}s")
        if proc.returncode != 0 or not os.path.exists(out_path):
            tail = "\n".join(stderr.strip().splitlines()[-20:])
            print(f"[sd-shim] sd-cli failed (exit {proc.returncode}): {tail}")
            raise RuntimeError(f"sd-cli failed (exit {proc.returncode}): {tail}")
        with open(out_path, "rb") as f:
            return f.read()


def parse_size(size: str) -> tuple[int, int]:
    try:
        w, h = size.lower().split("x")
        return int(w), int(h)
    except Exception:
        return 512, 512


class Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("[sd-shim] " + (fmt % args))

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "ok"})
        elif self.path == "/v1/models":
            self._json(200, {
                "object": "list",
                "data": [{"id": MODEL_ID, "object": "model", "owned_by": "local"}]
            })
        else:
            self._json(404, {"error": {"message": "not found"}})

    def do_POST(self):
        if self.path != "/v1/images/generations":
            self._json(404, {"error": {"message": "not found"}})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception as e:
            self._json(400, {"error": {"message": f"invalid request body: {e}"}})
            return

        prompt = body.get("prompt")
        if not prompt:
            self._json(400, {"error": {"message": "prompt is required"}})
            return
        n = int(body.get("n", 1))
        width, height = parse_size(body.get("size", "512x512"))

        try:
            images = []
            for i in range(n):
                seed = int(body.get("seed", -1))
                if seed < 0:
                    seed = uuid.uuid4().int & 0x7FFFFFFF
                png_bytes = run_generation(prompt, width, height, seed)
                images.append({"b64_json": base64.b64encode(png_bytes).decode()})
            self._json(200, {"created": int(time.time()), "data": images})
        except Exception as e:
            print(f"[sd-shim] request failed: {e}")
            status = 504 if "timed out" in str(e) else 500
            self._json(status, {"error": {"message": str(e)}})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"[sd-shim] listening on :{port}, model={MODEL_ID}, backend={BACKEND}")
    server.serve_forever()
