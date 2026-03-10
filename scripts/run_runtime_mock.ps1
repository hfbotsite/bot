$ErrorActionPreference = "Stop"

$env:PYTHONPATH = (Get-Location).Path
$env:BOT_CONFIG_PATH = "services/bot_runtime/example.bot.json"
$env:DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/bot"
$env:RUN_ID = "00000000-0000-0000-0000-000000000001"
$env:BOT_ID = "00000000-0000-0000-0000-000000000001"

$env:EXCHANGE_API_KEY = "dummy"
$env:EXCHANGE_API_SECRET = "dummy"
$env:EXCHANGE_API_PASSWORD = "dummy"

$env:SANDBOX = "true"
$env:MARKET_DATA_SOURCE = "mock"

python -m services.tools.run_runtime_once
