import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException


def create_app() -> FastAPI:
    app = FastAPI(
        title="HF Futures Public API",
        version="0.1.0",
    )

    orchestrator_base_url = os.getenv("ORCHESTRATOR_BASE_URL", "http://orchestrator:8002")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    async def proxy(method: str, path: str, json_body: Any | None = None) -> Any:
        url = f"{orchestrator_base_url}{path}"
        timeout = httpx.Timeout(10.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.request(method, url, json=json_body)
        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = {"detail": r.text}
            raise HTTPException(status_code=r.status_code, detail=detail)
        if r.content:
            return r.json()
        return None

    # Frontend contract: /api/v1/bots...
    # NOTE: authentication/rate limits should live here later; currently passthrough.
    @app.post("/api/v1/bots", status_code=201)
    async def create_bot(payload: dict[str, Any]) -> Any:
        # Map public payload -> internal orchestrator payload
        # Public expects: {name, runtime_version, config}
        # Temporary owner_id placeholder until auth is implemented.
        owner_id = str(payload.get("owner_id") or "u_demo")

        internal_payload = {
            "owner_id": owner_id,
            "name": payload.get("name") or "bot",
            "runtime_version": payload.get("runtime_version") or "latest",
            "config": payload.get("config") or {},
        }
        return await proxy("POST", "/internal/v1/bots", json_body=internal_payload)

    @app.get("/api/v1/bots/{bot_id}")
    async def bot_status(bot_id: str) -> Any:
        return await proxy("GET", f"/internal/v1/bots/{bot_id}")

    @app.post("/api/v1/bots/{bot_id}/stop")
    async def stop_bot(bot_id: str) -> Any:
        return await proxy("POST", f"/internal/v1/bots/{bot_id}/stop")

    @app.post("/api/v1/bots/{bot_id}/start")
    async def start_bot(bot_id: str) -> Any:
        return await proxy("POST", f"/internal/v1/bots/{bot_id}/start")

    @app.put("/api/v1/bots/{bot_id}/config")
    async def update_bot_config(bot_id: str, payload: dict[str, Any], restart: bool = True) -> Any:
        path = f"/internal/v1/bots/{bot_id}/config?restart={'true' if restart else 'false'}"
        internal_payload = {"config": payload.get("config") or {}}
        return await proxy("PUT", path, json_body=internal_payload)

    return app


app = create_app()
