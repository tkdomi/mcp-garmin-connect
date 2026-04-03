# mcp-garmin-connect

MCP server dla Garmin Connect — część ekosystemu Mia.

Wystawia narzędzia MCP umożliwiające Health Agentowi naturalną rozmowę o danych zdrowotnych użytkownika: sen, HRV, Body Battery, kroki, stres, aktywności fizyczne.

## Stack

- **Python 3.11+**
- **mcp** — oficjalne SDK Anthropic (Model Context Protocol)
- **garth** — komunikacja z Garmin Connect API
- **Supabase** — cache danych zdrowotnych
- **APScheduler** — codzienny sync o 7:00
- **httpx** — wysyłka webhooków do n8n

## Narzędzia MCP

| Tool | Opis |
|------|------|
| `get_sleep_data` | Sen, HRV, fazy snu dla podanej daty |
| `get_body_battery` | Aktualny poziom Body Battery i trend |
| `get_daily_stats` | Kroki, kalorie, minuty aktywności, stres |
| `get_last_activity` | Ostatnia aktywność fizyczna |
| `get_health_summary` | Tygodniowy/miesięczny przegląd zdrowia |

## Instalacja

```bash
git clone https://github.com/tkdomi/mcp-garmin-connect.git
cd mcp-garmin-connect

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# uzupełnij .env swoimi danymi
```

## Uruchomienie

```bash
python main.py
```

Serwer startuje na `http://0.0.0.0:8080` (domyślnie).

Dostępne endpointy:
- `GET /health` — status serwisu
- `POST /sync` — ręczny trigger synchronizacji
- `GET /sse` — MCP SSE transport

## Supabase — schemat bazy

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

## Zmienne środowiskowe

Patrz `.env.example`.

## Architektura

```
Health Agent (Voice/Chat)
      ↓
garmin-mcp (ten serwer, SSE transport)
      ↓
Garmin Connect API  +  Supabase cache  +  n8n webhooks
```
