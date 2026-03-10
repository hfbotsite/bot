import traceback

import psycopg

try:
    psycopg.connect(
        host="127.0.0.1",
        port=5432,
        dbname="backtest",
        user="backtest",
        password="backtest",
        connect_timeout=3,
    )
    print("connected")
except Exception as e:
    d = getattr(e, "diag", None)
    if d:
        keys = [
            "severity",
            "severity_nonlocalized",
            "sqlstate",
            "message_primary",
            "message_detail",
            "message_hint",
            "statement_position",
            "context",
            "source_file",
            "source_line",
            "source_function",
        ]
        for k in keys:
            print(f"{k}: {getattr(d, k, None)}")
    else:
        print("no diag")

    traceback.print_exc()

