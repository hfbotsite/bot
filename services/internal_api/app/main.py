from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(
        title="HF Futures Internal API",
        version="0.1.0",
    )

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
