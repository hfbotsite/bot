import py_compile

files = [
        "services/bot_engine/db.py",
        "services/bot_engine/engine_state.py",
        "services/bot_engine/fill_handler.py",
        "services/bot_engine/fills_repo.py",
        "services/bot_engine/positions_repo.py",
        "services/bot_engine/position_math.py",
        "services/bot_engine/events.py",
        "services/smoke_fill_pipeline.py",
        "services/execution/models.py",
        "services/execution/errors.py",
        "services/execution/intent_registry.py",
        "services/execution/transport_ccxt.py",
        "services/execution/hedge_normalizer.py",
        "services/execution/position_mode_manager.py",
        "services/execution/exchange_client.py",
        "services/execution/ohlcv.py",
        "services/execution/ohlcv_client.py",
        "services/execution/symbols.py",
    ]

ok = True
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print("OK", f)
    except Exception as e:
        ok = False
        print("FAIL", f, e)

print("ALL_OK" if ok else "HAS_FAIL")
