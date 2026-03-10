# Orchestrator: быстрый запуск бота из prebuilt image

## Архитектура

Frontend дергает Public API:

- `POST /api/v1/bots`
- `GET /api/v1/bots/{bot_id}`
- `POST /api/v1/bots/{bot_id}/stop`
- `POST /api/v1/bots/{bot_id}/start`
- `PUT /api/v1/bots/{bot_id}/config?restart=true`

Public API проксирует запросы во внутренний Orchestrator:

- `POST http://orchestrator:8002/internal/v1/bots`
- `GET  http://orchestrator:8002/internal/v1/bots/{bot_id}`
- `POST http://orchestrator:8002/internal/v1/bots/{bot_id}/stop`
- `POST http://orchestrator:8002/internal/v1/bots/{bot_id}/start`
- `PUT  http://orchestrator:8002/internal/v1/bots/{bot_id}/config?restart=true`

Orchestrator:
1) сохраняет конфиг в volume `/srv/bots/<bot_id>/config.json`
2) запускает контейнер `bot-<bot_id>` из образа `bot-runtime:<runtime_version>`
3) монтирует конфиг внутрь контейнера read-only

## Контракт payload (Frontend -> Public API)

### Создать бота

`POST /api/v1/bots`

```json
{
  "owner_id": "u_123",
  "name": "My bot",
  "runtime_version": "latest",
  "config": {
    "exchange": "bybit",
    "symbol": "BTCUSDT",
    "..."
  }
}
```

Ответ:

```json
{
  "bot_id": "b_<uuid>",
  "status": "running"
}
```

### Статус

`GET /api/v1/bots/{bot_id}`

Ответ:

```json
{
  "bot_id": "b_<uuid>",
  "status": "running|stopped|failed|creating|starting_container",
  "reason": null,
  "container_id": "...",
  "image": "bot-runtime:latest",
  "updated_at": "2026-03-09T20:00:00Z"
}
```

### Обновить конфиг

`PUT /api/v1/bots/{bot_id}/config?restart=true`

```json
{
  "config": {
    "...": "..."
  }
}
```

## Runtime (bot container) — контракт запуска (Этап 1)

Точка входа runtime контейнера: `python -m services.bot_runtime`.

Runtime читает конфиг и env в `services/bot_runtime/settings.py` (см. `BotSettings.load_from_env()`).

Обязательные переменные окружения для runtime:
- `BOT_ID`
- `BOT_CONFIG_PATH` — путь до config.json внутри контейнера (файл должен существовать)
- `DATABASE_URL`
- `EXCHANGE_API_KEY`
- `EXCHANGE_API_SECRET`

Опционально:
- `EXCHANGE_API_PASSWORD`
- `POSITION_MODE` (`hedge` | `one_way`, по умолчанию `hedge`)
- `CANDLES_WS_URL` (по умолчанию `ws://localhost:9999/ws`)
- `CANDLES_WS_STALE_AFTER_SECONDS` (по умолчанию `30`)
- `MARKET_DATA_SOURCE` (`ws` | `mock`, по умолчанию `ws`)
- `MOCK_SPEEDUP`, `MOCK_SEED`, `MOCK_START_PRICE` (для mock режима)
- `RUN_ID`
- `BOT_MODE=smoke` (для smoke-режима)

## Зависимости (Этап 1)

Зависимости разделены на 2 файла:
- `services/requirements.runtime.txt` — только runtime (`python -m services.bot_runtime`), без FastAPI/Docker SDK и без legacy `bot/`/`scipy`
- `services/requirements.orchestrator.txt` — только orchestrator/API

## Настройки окружения

### Public API

- `ORCHESTRATOR_BASE_URL` (по умолчанию `http://orchestrator:8002`)

### Orchestrator

- `BOT_CONFIG_ROOT` (по умолчанию `/srv/bots`)
- `BOT_IMAGE_REPO` (по умолчанию `bot-runtime`)
- `BOT_DOCKER_NETWORK` (опционально) — если контейнеры должны быть в конкретной docker network
- `DATABASE_URL` — пробрасывается в рантайм контейнер (если задан)

## Локальный запуск (docker compose)

Из каталога `services`:

```bash
docker compose up --build
```

Проверка:

- Public API: http://localhost:8010/health
- Orchestrator: http://localhost:8012/health

Smoke:

```bash
python -m services.tools.smoke_orchestrator
```

## Важно для продакшена (следующий шаг)

Текущая реализация хранит статус в памяти Orchestrator (dev-режим).
Для production нужно:
- хранить `bots` / `bot_runs` / `status` в Postgres
- healthcheck/heartbeat, чтобы `running` был подтвержденным
- лимитер параллельных стартов и идемпотентность create
- строгая JSON-schema валидация `config`
