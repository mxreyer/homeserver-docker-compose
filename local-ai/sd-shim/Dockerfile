# Pinned to a specific digest of the upstream project's own official Vulkan
# build (ghcr.io/leejet/stable-diffusion.cpp:master-vulkan at the time this
# was set up) rather than the floating tag, so a rebuild can't silently pick
# up a different upstream commit than what was actually tested here.
FROM ghcr.io/leejet/stable-diffusion.cpp@sha256:4412643c78248b7529d92273c47b9e90f446697270de0611c37fb09b24e366f5

RUN apt-get update && \
    apt-get install --yes --no-install-recommends python3 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY app.py /app.py

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python3", "/app.py"]
