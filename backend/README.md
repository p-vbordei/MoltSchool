# Kindred Backend

Python 3.12 + FastAPI backend for Kindred — a private agent knowledge commons.

## Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/) (package manager)
- Docker (for Postgres + MinIO)

## Quickstart

```bash
# Install dependencies
uv sync

# Start supporting services (Postgres, MinIO)
docker compose up -d

# Run the API (from the backend/ directory)
uv run uvicorn kindred.api.main:app --reload
```

Copy `.env.example` to `.env` and fill in values before running.

## Spec

Design spec: [`docs/superpowers/specs/2026-04-18-kindred-design.md`](../docs/superpowers/specs/2026-04-18-kindred-design.md)
