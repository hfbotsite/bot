# Trading Conventions v1 (Bybit Testnet, Linear USDT Perpetual, Hedge, Isolated)

## Цель документа

Этот документ фиксирует **единые торговые допущения** (конвенции), которые считаются “истиной” для первой итерации real trading.

Используется для:
- реализации контура исполнения (execution),
- нормализации сделок (fills),
- расчёта позиций и PnL,
- smoke-теста real trading,
- быстрого развёртывания на Ubuntu через Docker.

---

## 1) Биржа и рынок

- Exchange: **Bybit**
- Environment: **Testnet**
- Market type: **Perpetual futures**
- Contract type (Bybit): **Linear USDT (swap)**
- Основной инструмент smoke: **`ETH/USDT:USDT`**

---

## 2) Режимы позиции и маржи

- Position mode: **HEDGE**
  - На одном символе одновременно возможны две независимые позиции: `LONG` и `SHORT`.
  - Внутренний ключ позиции:  
    `(bot_run_id, symbol, position_mode="HEDGE", position_side in {"LONG","SHORT"})`

- Margin mode: **ISOLATED** (по умолчанию)
- Leverage: задаётся явно (фиксированное значение в конфиге на первом этапе)

---

## 3) Инварианты исполнения (обязательные правила)

### 3.1 Обязательные поля каждого торгового Intent

Любая торговая команда должна явно задавать:
- `symbol`
- `side`: `buy` / `sell`
- `position_side`: `LONG` / `SHORT`
- `reduce_only`: `true` / `false`
- `client_order_id` (для идемпотентности)

### 3.2 Запрет “случайного переворота” позиции

- Закрытие позиции выполняется **только** с `reduce_only=true` и корректным `position_side`.
- Запрещено:
  - `sell` без `reduce_only` при `position_side=LONG` как “закрытие” (может открыть SHORT)
  - `buy` без `reduce_only` при `position_side=SHORT` как “закрытие” (может открыть LONG)

---

## 4) Источник подтверждения сделок (fills)

Свечи (WS) используются только для сигналов и индикаторов.

**Факт исполнения сделок подтверждается только через fills**.

На первом этапе:
- основной источник: **polling через CCXT `fetchMyTrades`**
- дедупликация: уникальность по `(exchange, symbol, exchange_trade_id)`

---

## 5) Smoke real-trading test (testnet)

### Параметры
- Symbol: `ETH/USDT:USDT`
- Notional: **10 USDT**
- Order type: **market**
- Направление smoke: **LONG open + LONG close**

### Сценарий
1) Open LONG market на notional=10 USDT (`reduce_only=false`)
2) Дождаться fill (polling `fetchMyTrades`)
3) Close LONG market (`reduce_only=true`) на qty из позиции (или эквивалент notional)
4) Дождаться fill

### Критерии успеха
- В БД появились `trade_fills` (open/close) без дублей
- Позиция `(HEDGE, LONG)` корректно закрылась
- Записались `pnl_ledger_entries` для комиссии (и при наличии — realized pnl)

---

## 6) Логирование и безопасность

- Никогда не логировать значения API ключей/секретов.
- В логах должны быть:
  - факт соединения с биржей,
  - отправка ордера (без секретов),
  - получение fill,
  - успешная запись в БД.
