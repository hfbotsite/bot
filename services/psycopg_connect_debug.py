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
    print(type(e))
    print("msg:", e)
    print("diag:", getattr(e, "diag", None))
    print("sqlstate:", getattr(e, "sqlstate", None))
    print("pgcode:", getattr(e, "pgcode", None))
    print("pgerror:", getattr(e, "pgerror", None))

