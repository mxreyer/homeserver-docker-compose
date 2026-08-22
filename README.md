# Homeserver Docker Compose Setup

A collection of self-hosted services running via Docker Compose, configured with Tailscale for secure remote access.

## Services

| Service | Purpose | Details |
|---------|---------|---------|
| **Actual Budget** | Personal finance management | Budget tracking and account management |
| **Firefly III** | Financial transaction tracking | Double-entry accounting with data import support |
| **Immich** | Photo/video backup | Self-hosted photo library with ML features |
| **Nextcloud AIO** | File sync & collaboration | All-in-one cloud storage, contacts, calendar |
| **Mealie** | Recipe management | Recipe storage and meal planning |
| **Paperless** | Document management | OCR and document organization |
| **SearXNG** | Privacy-focused search | Meta-search engine aggregator |
| **Ollama** | Local LLM inference | Run language models locally |
| **Beszel** | Server monitoring | System metrics and monitoring |
| **Healthchecks** | Cron monitoring | Track scheduled job execution |
| **Stirling PDF** | PDF tools | PDF manipulation and conversion |
| **Borg4Pi** | Backup/archival | Automated backup with Borg |
| **Actual Helpers** | Budget utilities | Helper tools for Actual Budget |

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Tailscale account (for secure remote access)

### Setup Steps

1. **Clone and navigate to a service:**
   ```bash
   cd actual  # or firefly, immich, etc.
   ```

2. **Configure environment:**
   ```bash
   # Copy template to actual .env
   cp .env.template .env
   # Edit with your configuration
   nano .env
   ```

3. **Start services:**
   ```bash
   docker compose up -d
   ```

4. **Check status:**
   ```bash
   docker compose ps
   ```

## Configuration

Each service directory contains:
- `compose.yaml` — Docker Compose configuration
- `.env.template` — Environment variable template (copy to `.env`)
- `tailscale/` — Tailscale configuration for secure access

### Environment Variables

Services use environment variables for configuration. Templates are provided for each service:
- Copy `.env.template` to `.env`
- Update with your specific values
- `.env` files are gitignored for security

Key variables typically include:
- `CONF_HOSTNAME` — Tailscale node name
- `CONF_TS_KEY` — Tailscale authentication key
- `CONF_TS_TAG` — Tailscale tags for access control
- Service-specific credentials and URLs

## Architecture

```
homeserver-docker-compose/
├── actual/              # Actual Budget finance app
├── firefly/             # Firefly III accounting
├── immich/              # Photo library
├── mealie/              # Recipe management
├── nc-aio/              # Nextcloud all-in-one
├── paperless/           # Document management
├── searxng/             # Meta search engine
├── ollama/              # Local LLM runtime
├── beszel/              # Server monitoring
├── healthchecks/        # Cron job monitoring
├── stirling/            # PDF tools
├── borg4pi/             # Backup system
├── actual-helpers/      # Actual Budget helpers
└── README.md
```

Each service is independent and can be started/stopped individually.

## Common Operations

### Start a service
```bash
cd <service>
docker compose up -d
```

### Stop a service
```bash
cd <service>
docker compose down
```

### View logs
```bash
cd <service>
docker compose logs -f <service-name>
```

### Rebuild after config changes
```bash
cd <service>
docker compose up -d --force-recreate
```

## Storage

Services store data in `../../docker-binds/<service>/` (outside this repo) to:
- Preserve data across container restarts
- Keep repositories lean
- Simplify backup workflows

## Tailscale Integration

Most services use Tailscale for secure, private access:
- No exposed ports to public internet
- End-to-end encryption
- Easy remote access from any device

Configure per-service in:
- `tailscale/config/serve.json` — Access rules
- `.env` — Tailscale credentials

## Notes

- `.env` and `.*env` files are gitignored (sensitive data)
- Tailscale state directories are gitignored
- Borg backup data (`borg4pi/repo`, `borg4pi/data`) is gitignored
- Services use `restart: unless-stopped` by default

## License

Configuration and setup scripts are provided as-is.
