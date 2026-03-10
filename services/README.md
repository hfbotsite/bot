# Services (SaaS platform)


Этот каталог содержит новый серверный контур платформы (public-api/internal-api) и миграции PostgreSQL.


Текущий legacy-бот (Windows GUI, SQLite) находится в `bot/` и не затрагивается.


## Локальный запуск (docker-compose)


Требования:


- Docker Desktop / Docker Engine
- Порты на хосте:
  - PostgreSQL: `5433` (контейнерный `5432`)
  - public-api: `8010` (контейнерный `8000`)
  - internal-api: `8011` (контейнерный `8001`)


Запуск:


```bash
cd services
# первый раз:
copy .env.example .env
# заполните EXCHANGE_API_KEY / EXCHANGE_API_SECRET в .env (Bybit testnet)
docker compose up -d --build
```


Остановка:


```bash
cd services
docker compose down
```


## Smoke real-trading (Bybit testnet)

Запуск smoke внутри контейнера `bot-runtime` (market open/close LONG на `ETH/USDT:USDT`, notional=10 USDT):

```bash
cd services
docker compose run --rm -e BOT_MODE=smoke bot-runtime
```

Smoke использует переменные окружения из `.env`:
- `EXCHANGE_API_KEY`, `EXCHANGE_API_SECRET`
- `SANDBOX=true`
- `DATABASE_URL` (по умолчанию на `postgres` внутри docker сети)
- `RUN_ID` (bot_run_id для записи в БД)

## Проверка доступности API


```bash
curl http://localhost:8010/health
curl http://localhost:8011/health
```


OpenAPI:


- public-api: http://localhost:8010/openapi.json (или `/docs`)
- internal-api: http://localhost:8011/openapi.json (или `/docs`)


## Миграции (Alembic)


Миграции находятся в `services/migrations`.


Применить миграции:


```bash
cd services/migrations
alembic -c alembic.ini upgrade head
```


Сгенерировать новую миграцию (autogenerate):


```bash
cd services/migrations
alembic -c alembic.ini revision --autogenerate -m "your_message"
```


Примечания:


- В `alembic.ini` указан DSN по умолчанию для локальной разработки: `postgresql+psycopg://bot:bot@localhost:5433/bot_platform`
- При запуске в контейнерах сервисы подключаются к Postgres по внутреннему адресу `postgres:5432` (см. `services/docker-compose.yml`).
