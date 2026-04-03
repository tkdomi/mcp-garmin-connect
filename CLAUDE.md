# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Run
python main.py

# Manual sync trigger (server must be running)
curl -X POST http://localhost:8080/sync

# Health check
curl http://localhost:8080/health
```

## Architecture

This is a Python MCP (Model Context Protocol) server that bridges the Mia AI assistant ecosystem with Garmin Connect health data.

**Request flow:**
```
Mia Voice/Chat → NestJS Orchestrator → Health Agent → garmin-mcp (SSE transport)
                                                              ↓
                                               Garmin Connect API (via garth)
                                                              ↓
                                                     Supabase cache
                                                              ↓
                                                    n8n webhooks (alerts)
```

**Transport:** SSE (`/sse` endpoint) for network deployments on VPS. The MCP server is a Starlette ASGI app served by uvicorn.

**Key module responsibilities:**
- `main.py` — MCP server setup, all 5 tool registrations and implementations, REST endpoints (`/health`, `/sync`, `/sse`)
- `src/garmin_client.py` — `garth` wrapper with retry logic (`@with_retry` decorator, 3 attempts, exponential backoff); all Garmin API calls run via `asyncio.to_thread` since garth is sync
- `src/cache.py` — Supabase read/write with TTL logic; `get()` returns `None` on expiry, `get_stale()` ignores TTL for graceful degradation
- `src/scheduler.py` — APScheduler daily cron at `SYNC_HOUR:SYNC_MINUTE`; also sends n8n webhook after sync
- `src/alerts.py` — evaluates health metrics against configurable thresholds; builds `WebhookPayload`
- `src/models.py` — Pydantic v2 schemas for all data types; all fields `Optional` with `stale: bool` flag
- `src/config.py` — pydantic-settings `Settings` class; all config via `.env`

**Cache TTL:** `daily_stats`, `body_battery`, `activity` = `CACHE_TTL_DAILY` (default 1h); `sleep` = `CACHE_TTL_HISTORICAL` (default 24h). Cache keys are `(data_type, recorded_date)` pairs stored in the `health_data` Supabase table as JSONB.

**Garmin authentication:** `garth` stores session tokens locally at `~/.garth/`. On first call, `GarminClient._ensure_auth()` tries to resume the session; if that fails, it re-authenticates with credentials from env.

## Environment Variables

Required: `GARMIN_EMAIL`, `GARMIN_PASSWORD`

Optional (Supabase — enables caching): `SUPABASE_URL`, `SUPABASE_KEY`

Optional (n8n — enables webhook alerts): `N8N_WEBHOOK_URL`, `N8N_BEARER_TOKEN`

Optional (tuning): `MCP_PORT` (8080), `SYNC_HOUR` (7), `CACHE_TTL_DAILY` (1), `CACHE_TTL_HISTORICAL` (24), plus all `ALERT_*` threshold overrides.

## Supabase Schema

Migracje w `supabase/migrations/`. Zastosuj przez `supabase db push`.