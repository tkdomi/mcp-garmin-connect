# Garmin MCP Server — Product Requirements Document

**Projekt:** Mia Ecosystem  
**Komponent:** Health Module  
**Wersja:** 1.0.0  
**Data:** Marzec 2025  
**Autor:** Domi  
**Status:** Draft

---

## Spis treści

1. [Cel i kontekst projektu](#1-cel-i-kontekst-projektu)
2. [Wymagania funkcjonalne](#2-wymagania-funkcjonalne)
3. [Architektura techniczna](#3-architektura-techniczna)
4. [Wymagania niefunkcjonalne](#4-wymagania-niefunkcjonalne)
5. [Plan implementacji](#5-plan-implementacji)
6. [Przykłady użycia](#6-przykłady-użycia)
7. [Środowisko i deployment](#7-środowisko-i-deployment)

---

## 1. Cel i kontekst projektu

Garmin MCP Server to samodzielna usługa Python, która stanowi pomost między asystentem Mia a danymi zdrowotnymi użytkownika zgromadzonymi w Garmin Connect. Serwer implementuje protokół MCP (Model Context Protocol) firmy Anthropic, dzięki czemu Health Agent działający w ramach orkiestratora Mii może naturalnie rozmawiać o danych zdrowotnych użytkownika — bez konieczności rozbudowy backendu NestJS.

### 1.1 Problem

- Mia nie ma dostępu do danych zdrowotnych użytkownika — kroków, snu, HRV, Body Battery, aktywności fizycznych.
- Dane te są kluczowe dla korelacji z innymi modułami (finanse, nastrój, nauka języków).
- Garmin Connect nie udostępnia oficjalnego API dla end-userów, więc wymagana jest biblioteka reverse-engineered.
- Budowa dedykowanego modułu w NestJS wymagałaby Python bridge i tak — lepiej zbudować standalone serwis od razu w Pythonie.

### 1.2 Rozwiązanie

Osobna usługa Python, hostowana na tym samym VPS co n8n, która:

- Implementuje serwer MCP z zestawem narzędzi zdrowotnych (tools)
- Pobiera dane z Garmin Connect przez bibliotekę `garth`
- Cachuje dane w Supabase (unika częstych wywołań Garmin API)
- Udostępnia harmonogram synchronizacji (raz dziennie o 7:00)
- Wysyła webhooks do n8n w celu triggerowania alertów i powiadomień głosowych

### 1.3 Pozycja w ekosystemie Mii

```
Mia Voice/Chat
      ↓
NestJS Orchestrator
      ↓
Health Agent  ←→  garmin-mcp (ten serwer)
                        ↓
              Garmin Connect API
                        ↓
                   Supabase cache
                        ↓
                  n8n (alerty, raporty)
```

| Komponent | Rola |
|---|---|
| Mia Voice/Chat | Interfejs użytkownika — pyta o zdrowie głosowo lub tekstowo |
| NestJS Orchestrator | Routuje zapytania do Health Agenta |
| Health Agent | Interpretuje intencję, wywołuje narzędzia MCP |
| Garmin MCP Server | Wystawia tools, pobiera dane, cache w Supabase |
| n8n | Workflow alertów, powiadomień push, raportów |

---

## 2. Wymagania funkcjonalne

### 2.1 Narzędzia MCP (Tools)

Serwer wystawia pięć narzędzi dostępnych dla Health Agenta:

| Narzędzie | Opis | Parametry wejściowe |
|---|---|---|
| `get_sleep_data` | Jakość snu, fazy, HRV, czas w łóżku i czas snu | `date: YYYY-MM-DD` (opcj., domyślnie poprzednia noc) |
| `get_body_battery` | Aktualny poziom Body Battery i trend dzienny | brak |
| `get_daily_stats` | Kroki, kalorie, minuty aktywności, poziom stresu | `date: YYYY-MM-DD` (opcj., domyślnie dziś) |
| `get_last_activity` | Szczegóły ostatniej aktywności: typ, czas, HR, dystans | brak |
| `get_health_summary` | Tygodniowy/miesięczny przegląd — do korelacji z innymi danymi | `days: int` (domyślnie 7) |

### 2.2 Synchronizacja danych

- Automatyczny sync raz dziennie o 7:00 (APScheduler)
- Dane cachowane w Supabase — tabela `health_data`
- Przy zapytaniu MCP tool: najpierw sprawdź cache, dopiero potem Garmin API
- TTL cache: 1 godzina dla danych dziennych, 24 godziny dla danych historycznych
- Manual sync przez endpoint REST `POST /sync` (do celów deweloperskich)

### 2.3 Integracja z n8n

Po każdej synchronizacji serwer wysyła webhook do n8n z danymi zdrowotnymi i listą triggerów alertów:

```json
{
  "event": "health_synced",
  "body_battery": 45,
  "sleep_score": 62,
  "hrv": 38,
  "steps": 3200,
  "alert_triggers": ["low_body_battery", "poor_sleep"],
  "timestamp": "2025-03-17T07:00:00Z"
}
```

### 2.4 Progi alertów (domyślne, konfigurowalne)

| Metryka | Próg ostrzeżenia | Próg krytyczny | Trigger |
|---|---|---|---|
| Body Battery | < 40% | < 20% | `low_body_battery` / `body_battery_critical` |
| Jakość snu | < 65 | < 50 | `poor_sleep` / `sleep_critical` |
| HRV (odchylenie) | > 15% poniżej baseline | > 25% poniżej baseline | `low_hrv` |
| Poziom stresu | > 60 (avg. dzienny) | > 75 | `high_stress` / `stress_critical` |
| Kroki | < 5000 przed 20:00 | < 2000 koniec dnia | `low_steps` / `steps_critical` |

---

## 3. Architektura techniczna

### 3.1 Stack technologiczny

| Komponent | Technologia | Uzasadnienie |
|---|---|---|
| MCP framework | `mcp` (oficjalne SDK Anthropic) | Standard protokołu, aktywnie wspierany |
| Garmin API | `garth` | Najlepiej utrzymana biblioteka, obsługa OAuth |
| Cache / baza | Supabase (`supabase-py`) | Spójność z resztą ekosystemu Mii |
| Scheduler | APScheduler | Lekki, bez zależności zewnętrznych |
| HTTP (alerty) | `httpx` | Async-native, zastępuje `requests` |
| Serwer transport | stdio / SSE | stdio lokalnie, SSE dla połączeń sieciowych |
| Walidacja | pydantic v2 | Zgodność z resztą ekosystemu Python |

### 3.2 Struktura katalogów

```
garmin-mcp/
├── main.py                  # entry point, inicjalizacja MCP, rejestracja tools
├── src/
│   ├── __init__.py
│   ├── garmin_client.py     # wrapper na garth — pobieranie danych
│   ├── cache.py             # Supabase read/write, TTL logic
│   ├── scheduler.py         # APScheduler — codzienny sync + webhook
│   ├── models.py            # Pydantic schemas (SleepData, DailyStats, ...)
│   ├── alerts.py            # logika progów + payload builder
│   └── config.py            # zmienne env, stałe konfiguracyjne
├── tests/
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

### 3.3 Schemat bazy danych (Supabase)

Pojedyncza tabela `health_data` przechowuje wszystkie typy danych zdrowotnych jako JSONB:

```sql
CREATE TABLE health_data (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID REFERENCES auth.users(id),
  data_type     TEXT NOT NULL,   -- sleep | daily_stats | activity | body_battery
  recorded_date DATE NOT NULL,
  raw_data      JSONB NOT NULL,
  synced_at     TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, data_type, recorded_date)
);

CREATE INDEX idx_health_date ON health_data(data_type, recorded_date DESC);
```

### 3.4 Transport MCP

| Tryb | Kiedy używać | Konfiguracja |
|---|---|---|
| `stdio` | Mia i MCP server na tym samym hoście | NestJS uruchamia proces przez `spawn`, brak portu |
| `SSE` (HTTP) | MCP server na VPS, Mia backend zdalnie | `PORT=8080`, endpoint `/sse` |

> **Rekomendacja:** SSE — VPS hostuje zarówno n8n jak i garmin-mcp, połączenie przez sieć wewnętrzną VPS.

---

## 4. Wymagania niefunkcjonalne

### 4.1 Bezpieczeństwo

- Dane logowania Garmin przechowywane wyłącznie w zmiennych środowiskowych (`.env`), nigdy w kodzie
- Garmin session token cachowany lokalnie przez `garth` (`~/.garth/`), nie w Supabase
- Komunikacja MCP server ↔ NestJS zabezpieczona bearer tokenem
- Supabase: Row Level Security (RLS) na tabeli `health_data`
- VPS: garmin-mcp nasłuchuje wyłącznie na localhost lub w sieci wewnętrznej VPS

### 4.2 Wydajność

- Czas odpowiedzi MCP tool call: **< 200ms** (przy trafieniu w cache)
- Czas odpowiedzi MCP tool call: **< 3s** (przy miss cache + call do Garmin API)
- Codzienny sync: **< 60 sekund** dla pełnego zestawu danych
- Cache hit rate: **> 90%** dla zapytań w ciągu dnia

### 4.3 Niezawodność

- Graceful degradation: jeśli Garmin API niedostępne, zwróć dane z cache z flagą `stale: true`
- Retry logic: 3 próby z exponential backoff dla wywołań Garmin API
- Automatyczne odnawianie sesji `garth` (token expiry handling)
- Logi błędów do pliku + opcjonalnie webhook do n8n w przypadku awarii synca

### 4.4 Utrzymanie

- Konfiguracja przez `.env` — zero zmian kodu przy zmianie środowiska
- Progi alertów konfigurowalne przez zmienne środowiskowe
- Endpoint `GET /health` dla monitoringu stanu serwisu
- Endpoint `POST /sync` dla ręcznego wyzwolenia synchronizacji

---

## 5. Plan implementacji

### 5.1 Etapy

| # | Etap | Zakres | Wynik |
|---|---|---|---|
| 1 | Garmin Client | `garmin_client.py`, `config.py`, weryfikacja połączenia z Garmin API, pobranie pierwszych danych | Dane z Garmina wchodzą |
| 2 | Cache Layer | `cache.py`, schemat Supabase, zapis/odczyt, TTL logic | Dane persystowane w Supabase |
| 3 | MCP Tools | `main.py`, `models.py`, rejestracja 5 tools, transport SSE | Agent może wywołać tools |
| 4 | Scheduler + Alerty | `scheduler.py`, `alerts.py`, webhook do n8n | Codzienny sync + powiadomienia |
| 5 | Integracja z Mią | Podłączenie Health Agenta w NestJS, testy end-to-end głosowe | Mia odpowiada na pytania zdrowotne |

Etapy 1 → 2 → 3 muszą być wykonane sekwencyjnie. Etap 4 można realizować równolegle z etapem 3 po ukończeniu etapu 2. Etap 5 wymaga gotowości wszystkich poprzednich etapów.

### 5.2 Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Mitigacja |
|---|---|---|
| Garmin zmieni API — biblioteka `garth` przestanie działać | Średnie | Izolacja w `garmin_client.py` — wymiana biblioteki bez zmian w reszcie kodu |
| Blokada konta Garmin przy zbyt częstych zapytaniach | Niskie | Cache TTL, maks. 1 sync dziennie, rate limiting w kliencie |
| Awaria VPS — utrata dostępu do serwisu | Niskie | Graceful degradation w NestJS — Health Agent zwraca ostatnie dane z Supabase |
| Zmiana formatu danych Garmin Connect | Średnie | Pydantic schemas + walidacja przy zapisie do cache — błędy wykryte od razu |

---

## 6. Przykłady użycia

### 6.1 Zapytania głosowe

| Użytkownik mówi | Tool wywołany | Efekt |
|---|---|---|
| "Jak spałem zeszłej nocy?" | `get_sleep_data()` | Mia zwraca wynik snu, HRV, fazy snu w naturalnym języku |
| "Ile mam teraz energii?" | `get_body_battery()` | Mia mówi "Twoje Body Battery wynosi 67, jesteś w dobrej formie" |
| "Co robiłem dziś aktywnego?" | `get_last_activity()` + `get_daily_stats()` | Podsumowanie aktywności i kroków za dzień |
| "Podsumuj mój tydzień zdrowotnie" | `get_health_summary(days=7)` | Tygodniowy raport z trendami |

### 6.2 Korelacja z innymi modułami Mii

- **Finanse + zdrowie:** "Czy wydaję więcej w dni, gdy mam niski Body Battery?" → Health Summary + dane finansowe z Supabase
- **Nauka języków:** "Zaplanuj sesję angielskiego na dziś" → Mia sprawdza Body Battery i HRV przed zaproponowaniem intensywności
- **Smart home:** Low Body Battery trigger → n8n przyciemnia światła, zmienia tryb termostatu

---

## 7. Środowisko i deployment

### 7.1 Zmienne środowiskowe

| Zmienna | Wymagana | Opis |
|---|---|---|
| `GARMIN_EMAIL` | Tak | Email konta Garmin Connect |
| `GARMIN_PASSWORD` | Tak | Hasło konta Garmin Connect |
| `SUPABASE_URL` | Tak | URL projektu Supabase |
| `SUPABASE_KEY` | Tak | Service role key Supabase |
| `N8N_WEBHOOK_URL` | Tak | URL webhooka n8n dla alertów |
| `N8N_BEARER_TOKEN` | Tak | Token autoryzacyjny n8n |
| `MCP_PORT` | Nie | Port serwera MCP SSE (domyślnie `8080`) |
| `SYNC_HOUR` | Nie | Godzina codziennego synca (domyślnie `7`) |
| `CACHE_TTL_DAILY` | Nie | TTL cache dla danych dziennych w godzinach (domyślnie `1`) |
| `CACHE_TTL_HISTORICAL` | Nie | TTL cache dla danych historycznych w godzinach (domyślnie `24`) |
| `ALERT_BODY_BATTERY_WARNING` | Nie | Próg ostrzeżenia Body Battery (domyślnie `40`) |
| `ALERT_BODY_BATTERY_CRITICAL` | Nie | Próg krytyczny Body Battery (domyślnie `20`) |
| `ALERT_SLEEP_SCORE_WARNING` | Nie | Próg ostrzeżenia jakości snu (domyślnie `65`) |
| `ALERT_SLEEP_SCORE_CRITICAL` | Nie | Próg krytyczny jakości snu (domyślnie `50`) |
| `ALERT_STRESS_WARNING` | Nie | Próg ostrzeżenia stresu (domyślnie `60`) |
| `ALERT_STRESS_CRITICAL` | Nie | Próg krytyczny stresu (domyślnie `75`) |

### 7.2 Hosting

- Środowisko docelowe: VPS (ten sam serwer co n8n)
- Proces zarządzany przez `pm2` lub `systemd`
- Garmin session token persystowany lokalnie przez `garth` (`~/.garth/`)
- Logi do `/var/log/garmin-mcp/` z rotacją 7 dni

### 7.3 Wymagania systemowe

- Python 3.11+
- RAM: ~128 MB
- Dysk: ~50 MB (+ logi)
- Sieć: dostęp do `api.garmin.com` i Supabase

### 7.4 Uruchomienie

```bash
# Klonowanie repo
git clone https://github.com/tkdomi/mcp-garmin-connect.git
cd mcp-garmin-connect

# Środowisko wirtualne
python -m venv venv
source venv/bin/activate

# Zależności
pip install -r requirements.txt

# Konfiguracja
cp .env.example .env
nano .env

# Start
python main.py
```

Dostępne endpointy po uruchomieniu:

- `GET  /health` — status serwisu
- `POST /sync` — ręczny trigger synchronizacji
- `GET  /sse` — MCP SSE transport endpoint
