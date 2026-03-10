# Hedge Grid MVP (BO/SO + Exit: Squeeze + TP(Market) + SL)

## Что добавлено

### Strategy (`services/bot_engine/strategy.py`)
Стратегия теперь генерирует `desired_orders` в hedge mode отдельно для каждой стороны позиции (`LONG` и `SHORT`):

1. **Если позиции нет (FLAT)**:
   - строится сетка BO/SO от reference-цены (`PriceFeed.latest_price(...).price`)
   - на биржу выставляются уровни сетки в зависимости от `basic.active_orders`:
     - `active_orders = 0` → только следующий уровень (в FLAT это BO, индекс 0)
     - `active_orders > 0` → первые `N` уровней

2. **Если позиция есть**:
   - выставляется **Squeeze LIMIT** (reduceOnly), если `exit.squeeze_profit > 0`
     - для `LONG` цена выше TP
     - для `SHORT` цена ниже TP
   - выставляется **TP conditional MARKET fallback** (reduceOnly) по `exit.exit_profit_level`
     - работает как страховка: если squeeze limit не исполнился, позиция закроется market-ордером по триггеру
     - `triggerBy = MarkPrice`
   - выставляется **Stop-loss conditional MARKET** (reduceOnly), если `exit.exit_stop_loss_level > 0`
     - `triggerBy = MarkPrice`
   - выставляется продолжение сетки (baseline): уровни с `filled_levels=1` (предполагаем, что BO уже был исполнен)

### Grid math (`services/bot_engine/position_math.py`)
Добавлены чистые функции:
- `build_grid_levels(...) -> list[GridLevel]` — детерминированно строит уровни BO+SO (цена/объём)
- `select_active_grid_indices(...) -> list[int]` — выбирает индексы уровней, которые должны быть активны на бирже

### client_order_id (идемпотентность)
Форматы:
- TP (conditional market): `{bot_id}-tp-{symbol}-{position_side}`
- Squeeze limit: `{bot_id}-squeeze-{symbol}-{position_side}`
- Stop-loss (conditional market): `{bot_id}-sl-{symbol}-{position_side}`
- Grid: `{bot_id}-grid-{symbol}-{position_side}-{index}`

Важно: prefix `{bot_id}-` обязателен, т.к. `OrderManager` фильтрует “наши” ордера по этому префиксу.

## Единицы измерения (важно)

Поля, которые трактуются как **проценты** (значение `0.5` => `0.5%`):
- `exit.exit_profit_level` (TP trigger)
- `exit.squeeze_profit` (отступ squeeze относительно TP)
- `exit.exit_stop_loss_level` (SL отступ относительно avg entry)
- `grid.first_step`
- `grid.range_cover`

Внутри стратегии они нормализуются в доли (`/100`).

## Fills pipeline / сделки (deals)

### Модель
- Сделка (`deals`) открывается при первом фактическом появлении позиции по fills (переход qty: 0 -> != 0).
- Сделка закрывается только по факту закрытия позиции (переход qty: != 0 -> 0).
- `exit_reason` пишется при закрытии сделки и должен отражать *фактическую причину закрытия* (по закрывающим reduce fills).

### Реализация (MVP)
- `services/bot_engine/fill_handler.py`:
  - открытие: `DealsRepo.ensure_open_deal(...)`
  - закрытие: `DealsRepo.close_deal(..., exit_reason=...)`
  - постановка причины выхода: при reduce fill (`closed_qty_abs > 0`) и наличии `fill.exit_reason` ставится `ExitTracker.set_exit_intent(...)`.
- `services/bot_engine/exit_tracker.py`:
  - in-memory трекер причины выхода до фактического закрытия по fills (qty -> 0).
  - поддерживаемые причины: `squeeze_exit`, `tp_market_exit`, `stop_loss_exit`, `indicators_exit`.

### Как определяется exit_reason (pipeline)
1. При создании reduceOnly ордера:
   - `services/execution/exchange_client.py` определяет `exit_reason` по `client_order_id` и сохраняет в `OrderIntentRegistry`.
2. При получении трейдов:
   - `ExecutionClient.fetch_my_trades()` пытается найти intent по `client_order_id` и прокидывает причину как `_exit_reason` в `NormalizedFill.raw`.
3. При ingest fills в runtime:
   - `services/bot_runtime/runtime.py` переносит `_exit_reason` в `FillEvent.exit_reason`.
4. При обработке fill в движке:
   - `services/bot_engine/fill_handler.py` по закрывающим fills ставит `ExitIntent`, и при qty->0 пишет `deals.exit_reason`.

Важно:
- Fallback на `"tp_market_exit"` убран. Если причину определить не удалось, `deals.exit_reason` будет `NULL` (и это сигнал, что нужно улучшить атрибуцию).

### Конвенции client_order_id для причин выхода
- Squeeze limit: содержит `-squeeze-` → `squeeze_exit`
- TP conditional market: содержит `-tp-` → `tp_market_exit`
- SL conditional market: содержит `-sl-` → `stop_loss_exit`
- Выход по индикаторам (market по сигналу): содержит `-exit-ind-` → `indicators_exit`
  - пример: `{bot_id}-exit-ind-stoch_cci-{symbol}-{position_side}`


## Smoke запуск (mock)

Скрипт:
- `scripts/run_runtime_mock.ps1`

Примечание:
- В mock режиме позиции/филлы не подгружаются, поэтому этот smoke в основном проверяет:
  - что runtime стартует
  - что нет утечек aiohttp/ccxt resources
  - что стратегия/математика компилируются и могут быть вызваны

## Переключение таймфрейма для усреднения (MVP)

### Цель
В режиме усреднения (когда есть открытая позиция) бот может переключать таймфрейм, на котором считается **сигнал `averaging`** (и, следовательно, разрешение на выставление market-усреднения в `AveragingCoordinator`).

Важно:
- это **не UI-переключатель**, а часть торговой логики runtime
- вход (`entry`) и выход (`exit`) в этом MVP **не переключаются**, изменяется только TF для `averaging`-сигнала

### Конфигурация
Цепочка таймфреймов задаётся в `averaging.timeframe` как строка через запятую:

```json
"averaging": {
  "enabled": true,
  "timeframe": "5m, 15m, 1h, 4h",
  ...
}
```

- первый элемент цепочки — **base timeframe**
- в runtime свечи прогреваются/стримятся для всех таймфреймов из цепочки (см. `BotSettings.working_timeframes`)

Включение логики переключения:
- `timeframe_switching.timeframe_switching = true`
- `timeframe_switching.ema_global_switch = true`

Триггерный таймфрейм EMA:
- берётся из `indicators_tuning.global_timeframe` (например `1h`)

### Триггер (EMA200 cross на global timeframe)
Реализован EMA200 cross по close на `indicators_tuning.global_timeframe`:

- для LONG: `close` пересёк EMA200 **сверху вниз** → шаг вверх по цепочке
- для SHORT: `close` пересёк EMA200 **снизу вверх** → шаг вверх по цепочке

Примечание: в MVP используется один “active averaging tf” на весь бот. Если произошёл любой из двух кроссов (down или up), выполняется step-up.

### Ограничение: переключение только при наличии позиции
Переключение разрешено только если у бота есть открытая позиция (LONG или SHORT):
- если позиция отсутствует (FLAT) → активный TF сбрасывается на base timeframe
- если позиция есть → разрешён step-up по EMA-cross

### Где реализовано
- `services/bot_runtime/timeframe_switcher.py` — логика цепочки + EMA200 cross
- `services/bot_runtime/settings.py` — парсинг `averaging.timeframe` как списка (CSV) и включение всех TF цепочки в `working_timeframes`
- `services/bot_runtime/runtime.py`
  - определение `has_position` (по position snapshots)
  - пересчёт `averaging`-сигнала на текущем active TF через “settings view” (подмена только `averaging.timeframe`)

### Что НЕ реализовано в этом MVP
- `orders_switch`, `last_candle_switch` и связанные параметры
- cooldown/revert политика (кроме reset на base при FLAT)
- разные active TF для LONG и SHORT (нужна переработка `SignalStore` под ключ `(symbol, position_side, event)`)

## Unification layer: Transport + ExchangeAdapter (CCXT)

### Зачем
По мере добавления новых бирж (Bybit/OKX/Binance/…) код начинает “пухнуть” от `if exchange == ...` в:
- транспорте (init options / hacks),
- нормализаторах (hedge params, stop params),
- мапперах (positions/trades).

Чтобы локализовать биржевую специфику и сохранить доменный API, введён слой адаптеров.

### Архитектура
```
ExecutionClient (Normalized* API)
   ↓
ExchangeAdapter (биржевая специфика: opts/params/mapping/symbols)
   ↓
CcxtAsyncTransport (retry/timeout/rate-limit + raw ccxt calls)
   ↓
ccxt.async_support.<exchange>
```

### Что где находится
- `services/execution/transport_ccxt.py`
  - `CcxtAsyncTransport`:
    - владеет ccxt exchange инстансом
    - retry/backoff + маппинг ошибок
    - `open()/load_markets()/close()`
    - `markets()` и `market(symbol)` для метаданных рынков
  - exchange-specific “хаки” из транспорта убраны; вместо этого есть `adapter_opts`, которые подмешиваются при создании exchange.

- `services/execution/adapters/`
  - `base.py`: `BaseCcxtAdapter` (MVP поведение по умолчанию)
    - hedge params (перенесены из `HedgeModeNormalizer`)
    - symbol resolve `BASE/QUOTE` -> ccxt symbol через `resolve_ccxt_symbol(markets=...)`
    - mapping: raw ccxt order/trade/positions -> `Normalized*`
  - `bybit.py`: `BybitAdapter`
    - `fetchCurrencies=False` (чтобы `load_markets()` не падал из‑за лишних permissions)
    - `orderLinkId -> clientOrderId` в trades
  - `registry.py`: `get_adapter(exchange_id)` — фабрика/реестр

- `services/execution/exchange_client.py`
  - `ExecutionClient` теперь принимает `adapter` и делегирует ему:
    - `build_create_order()`
    - `normalize_create_order_call()` (precision/min limits)
    - `map_order/map_trade/map_positions()`
  - В клиенте остаётся доменная логика:
    - `OrderIntentRegistry`

## Symbol conventions (spot-like vs swap/futures)

- Канонический symbol внутри системы (конфиг/стратегия/БД/логика): **`BASE/QUOTE`**, например `BTC/USDT`.
- Для CCXT swap/futures некоторые биржи требуют формат **`BASE/QUOTE:SETTLE`**, например `BTC/USDT:USDT`.
- Конвертация выполняется на границе с CCXT через `services/execution/symbols.py`:
  - `build_symbol_candidates()` генерирует кандидаты (`BTC/USDT:USDT` и `BTC/USDT`)
  - `resolve_ccxt_symbol(markets, base, quote, market)` выбирает корректный символ по `markets` после `load_markets()`
- В runtime:
  - вычисляется `self._ccxt_symbol` один раз при старте (`BotRuntime.start`)
  - все CCXT вызовы для market-data/execution используют `self._ccxt_symbol`
  - внутренняя логика (CandleStore/PriceFeed/StrategySupervisor/PositionsReader) продолжает работать с каноническим `settings.symbol` (`BASE/QUOTE`)

## Market rules (precision/min limits)

### Зачем это нужно
Биржи требуют:
- округлять цену/количество до допустимой точности (tick/step),
- не отправлять ордера меньше `min_amount` и иногда `min_cost`.

Без этого ордера могут отклоняться, а расчёты сетки/TP/SL будут “на бумаге”, но не исполнимы на рынке.

### Как реализовано сейчас (MVP)
- `services/execution/transport_ccxt.py`:
  - при `open()` выполняется `load_markets()` (ccxt уже подтягивает метаданные рынков)
  - добавлен метод `market(symbol)` для доступа к `exchange.market(symbol)` (precision/limits/contractSize)
- `services/execution/market_rules.py`:
  - `MarketRules.from_ccxt_market(...)` нормализует данные рынка
  - `round_price(...)`, `round_amount(...)` — округление вниз по количеству знаков
  - `validate_min_limits(...)` — проверка min_amount/min_cost
- `services/execution/exchange_client.py`:
  - в `create_order()` перед отправкой в ccxt:
    - подтягиваются правила рынка через `transport.market(call.symbol)`
    - amount/price округляются
    - выполняется проверка min limits (best-effort); если ниже лимитов — бросаем `ExchangeParamValidationError`

Примечание:
- В этом MVP используется округление “вниз” по количеству знаков (`precision`). Для бирж, где важны именно `tickSize/stepSize`, следующим шагом можно заменить/расширить логику на округление по шагу (step) из `market["info"]`.

## Что не реализовано в MVP
- определение `exit_reason` **без** корректной атрибуции `client_order_id` (например: ручные/внешние закрытия, биржа не вернула client id)
  - сейчас `exit_reason` определяется по закрывающим reduce fills **через intent**, привязанный к нашему `client_order_id`
  - “чистая” детекция по полям биржи (order type/stop params/trigger info) и/или персистентный маппинг `exchange_order_id -> reason` в БД — следующий шаг
- тесты на `build_symbol_candidates/resolve_ccxt_symbol` (сейчас покрыто только smoke/compile_check)
- индикаторные условия входа/усреднения (вход)

## Индикаторные события: Entry / Averaging / Exit

### Общая идея
В runtime считается 3 независимых сигнала (на каждый symbol):
- `entry` — сигнал на первичный вход (открытие позиции/старт сетки)
- `averaging` — сигнал на разрешение усреднения (выставление SO уровней)
- `exit` — сигнал на принудительный выход (reduceOnly market) с причиной `indicators_exit`

Сигналы считаются в `services/bot_runtime/signal_resolver.py` и кладутся в in-memory `SignalStore` (`services/bot_runtime/signal_store.py`).
Runtime крутит отдельный цикл перерасчёта сигналов (`BotRuntime._signals_loop`) и передаёт `SignalStore` в стратегию.

### Пресеты
Для каждого события выбирается один пресет (строка):
- Entry: `settings.entry.entry_preset`
- Averaging: `settings.averaging.avg_preset`
- Exit: `settings.exit.exit_preset` (`NONE` = выключено)

Поддерживаемые значения (на уровне resolver):
- `MA_CROSS`
- `STOCH_CCI`
- `STOCH_RSI`
- `CCI_CROSS`
- `RSI_SMARSI_CROSS`

Настройки пресетов лежат в соответствующих секциях конфига:
- `entry.ma_cross`, `entry.stoch_cci`, `entry.stoch_rsi`, `entry.cci_cross`, `entry.rsi_smarsi_cross`
- `averaging.ma_cross`, `averaging.stoch_cci`, `averaging.stoch_rsi`, `averaging.cci_cross`, `averaging.rsi_smarsi_cross`
- `exit.ma_cross`, `exit.stoch_cci`, `exit.stoch_rsi`, `exit.cci_cross`, `exit.rsi_smarsi_cross`

### Логика использования сигналов в стратегии
Файл: `services/bot_engine/strategy.py`

#### Entry
- `entry.entry_by_indicators = true`:
  - вход/старт сетки разрешён только если `SignalStore(entry)` даёт сигнал нужной стороны (`long` для `LONG`, `short` для `SHORT`)
- `entry.entry_by_indicators = false`:
  - вход по рынку (market) при прохождении фильтров EMA200 / Global STOCH
  - в текущем MVP фильтры как placeholder (если включены — вход запрещён до реализации вычислений)

#### Averaging (Dynamic Virtual Grid + Async Monitor)

В этом MVP усреднение реализовано как **виртуальная динамическая сетка** (dynamic grid) и **асинхронный монитор**, а не как заранее выставленные SO-лимитки.

Ключевые свойства:
- реальные averaging-ордера **не выставляются заранее**
- мониторинг запускается **только** при пересечении виртуального уровня
- averaging-ордер создаётся **market** (по требованию продукта)
- в качестве цены сравнения используется **MarkPrice**

##### Где реализовано
- Модуль: `services/bot_engine/dynamic_averaging.py`
  - `DynamicAveragingGrid` — расчёт виртуальных уровней
  - `AveragingCoordinator` — state + async monitor + защита от дублей
- Интеграция: `services/bot_runtime/runtime.py` (`BotRuntime._strategy_loop`)
  - `await avg.tick(...)` — быстрый “тик” координатора
  - `decision.desired_orders.extend(avg.consume_orders(...))` — добавление созданных market averaging intents в reconcile
- В `services/bot_engine/strategy.py` **убран** “averaging-signal gating” для continuation grid: теперь сигнал влияет только на averaging через monitor.

##### Виртуальные уровни (legacy formula)
Параметры (читаются из config):
- `range_cover` (%), базовый отступ (минимальный шаг)
- `first_so_coeff`
- `dynamic_so_coeff`

Первое усреднение:
- LONG: `price_1 = entry - entry * (first_so_coeff * range_cover / 100)`
- SHORT: `price_1 = entry + entry * (first_so_coeff * range_cover / 100)`

Последующие уровни (сетка расширяется):
- LONG: `price_N = last - last * (range_cover * dynamic_so_coeff ** i) / 100`
- SHORT: `price_N = last + last * (range_cover * dynamic_so_coeff ** i) / 100`

Где:
- `entry` — текущая средняя цена входа позиции (в MVP берём `avg_entry_price` из snapshot)
- `last` — “якорь” последнего усреднения (в MVP это MarkPrice в момент создания market-ордера)
- `i` — номер усредняющего ордера (1..N). В коде это `so_index` (0 означает “ещё не было усреднений”).

##### Условия старта/остановки мониторинга (LONG/SHORT зеркально)
- LONG:
  - если `MarkPrice <= next_level` → старт async-монитора
  - если `MarkPrice > next_level` → монитор немедленно завершается
- SHORT:
  - если `MarkPrice >= next_level` → старт async-монитора
  - если `MarkPrice < next_level` → монитор немедленно завершается

Таким образом монитор всегда привязан к:
- уровню **первого усреднения**, если `so_index == 0`
- уровню, рассчитанному от **последнего усреднения**, если `so_index > 0`

##### Гейтинг по индикаторам
Внутри мониторинга проверяется `SignalStore(event="averaging")`:
- для LONG нужен `signal.side == "long"`
- для SHORT нужен `signal.side == "short"`
- иначе монитор продолжает ждать, ничего не выставляя

##### Защита от повторных ордеров (new_order_time)
Чтобы индикаторы не провоцировали повторное усреднение сразу после выставления ордера, применяется cooldown:
- `new_order_time` (сек), типично 120s

Правило:
- после создания averaging market-ордера фиксируется `cooldown_until = now + new_order_time`
- следующее averaging возможно только после `cooldown_until`

##### Состояние усреднения (вместо БД-флага)
В MVP состояние хранится в памяти процесса (per `(symbol, position_side)`):
- `so_index` — счётчик усреднений
- `last_anchor_price` — якорь (MarkPrice на момент последнего averaging ордера)
- `cooldown_until`
- `monitor_task` + `monitor_id`

Сброс:
- при закрытии позиции (qty==0 или avg_entry_price=None) state сбрасывается и монитор останавливается.

##### Anti-dup / Anti-race гарантии
- **duplicate monitors**: один активный монитор на ключ, контроль через `monitor_task` + `monitor_id` (generation)
- **race conditions**: per-key `asyncio.Lock` вокруг start/stop монитора и создания averaging-ордера
- **duplicate orders**: `cooldown_until` + дополнительный `fingerprint` (страховка от повторов при неблагоприятных таймингах)

##### Режим цикла стратегии (sleep)
При открытой позиции runtime всё ещё может ускорять опрос стратегии до `averaging.avg_timesleep`, но сам факт усреднения теперь не зависит от того, возвращает ли StrategySupervisor grid-лимитки — averaging решается монитором.

#### Exit
- если `SignalStore(exit)` даёт противоположный сигнал:
  - LONG закрывается при `exit.side == "short"`
  - SHORT закрывается при `exit.side == "long"`
  - создаётся reduceOnly market-ордер с `client_order_id` содержащим `-exit-ind-`
  - `deals.exit_reason` будет `indicators_exit` (через intent registry)

Примечание: режим выхода выбирается через `exit.take_profit`:
- `profit_exit` — используется squeeze/tp/sl
- `indicators_exit` — выход по индикаторному сигналу (reduceOnly market)
- точная логика прогресса по сетке через fills (пока baseline `filled_levels=1` при наличии позиции)
- lift/перестроение сетки
