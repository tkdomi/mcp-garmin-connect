# mcp-garmin-connect

MCP server for Garmin Connect. Exposes health and activity data as MCP tools, enabling AI assistants to have natural conversations about your health metrics: sleep, HRV, Body Battery, steps, stress, and detailed workout data.

## Stack

- **Python 3.11+**
- **mcp** — Anthropic Model Context Protocol SDK
- **garth** — Garmin Connect API client
- **Supabase** — health data cache (optional)
- **APScheduler** — daily sync at configurable time
- **httpx** — n8n webhook delivery (optional)

## MCP Tools

| Tool | Description |
|------|-------------|
| `get_sleep_data` | Sleep quality, duration, phases (deep/light/REM), HRV, resting HR for a given date |
| `get_body_battery` | Current Body Battery level (0–100) and today's charge/drain trend |
| `get_daily_stats` | Steps, calories, active minutes, stress level for a given date |
| `get_activities` | List of activities filtered by sport type and/or time period (today, this_week, this_month…) |
| `get_activity` | Full activity details: per-km splits, cadence, power, stride metrics, training effect |
| `get_health_summary` | Multi-day health overview: avg sleep score, HRV, steps, stress, activity count |

## Installation

```bash
git clone https://github.com/tkdomi/mcp-garmin-connect.git
cd mcp-garmin-connect

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# fill in your credentials
```

## Running

```bash
python main.py
```

Server starts on `http://0.0.0.0:8080` by default.

Endpoints:
- `GET /health` — service status
- `POST /sync` — manual sync trigger
- `GET /sse` — MCP SSE transport

## Environment Variables

See `.env.example`. Required: `GARMIN_EMAIL`, `GARMIN_PASSWORD`.

Supabase (`SUPABASE_URL`, `SUPABASE_KEY`) and n8n (`N8N_WEBHOOK_URL`, `N8N_BEARER_TOKEN`) are optional.

## Supabase Schema

```sql
CREATE TABLE health_data (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID REFERENCES auth.users(id),
  data_type     TEXT NOT NULL,
  recorded_date DATE NOT NULL,
  raw_data      JSONB NOT NULL,
  synced_at     TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, data_type, recorded_date)
);

CREATE INDEX idx_health_date ON health_data(data_type, recorded_date DESC);
```

## Architecture

```
AI Assistant (Voice/Chat)
        ↓
garmin-mcp  (this server, SSE transport)
        ↓
Garmin Connect API  +  Supabase cache  +  n8n webhooks
```
