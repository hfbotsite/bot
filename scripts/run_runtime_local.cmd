@echo off
setlocal

REM Local runtime launcher (Windows cmd.exe)
REM Uses set "VAR=VALUE" to avoid trailing spaces in env vars.

set "BOT_CONFIG_PATH=services\bot_runtime\example.bot.json"
set "BOT_ID=39dab4d4-4eab-4d20-b7db-e4256edc5bb6"
set "RUN_ID=be31c4b5-b543-4d9b-a486-49722a793365"
set "DATABASE_URL=postgresql+psycopg://bot:bot@localhost:5433/bot_platform"
set "LOG_LEVEL=INFO"

python -m services.bot_runtime

endlocal
