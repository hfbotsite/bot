from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import docker
from docker.errors import NotFound
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BotCreateRequest(BaseModel):
    owner_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    runtime_version: str = Field(..., min_length=1)
    config: dict[str, Any]


class BotCreateResponse(BaseModel):
    bot_id: str
    status: Literal["creating", "starting_container", "running", "failed"]
    reason: str | None = None


class BotStatusResponse(BaseModel):
    bot_id: str
    status: Literal["creating", "starting_container", "running", "stopped", "failed"]
    reason: str | None = None
    container_id: str | None = None
    image: str | None = None
    updated_at: datetime


class BotConfigUpdateRequest(BaseModel):
    config: dict[str, Any]


def create_app() -> FastAPI:
    app = FastAPI(title="HF Futures Orchestrator", version="0.1.0")

    config_root = Path(os.getenv("BOT_CONFIG_ROOT", "/srv/bots"))
    image_repo = os.getenv("BOT_IMAGE_REPO", "bot-runtime")
    network_name = os.getenv("BOT_DOCKER_NETWORK", "")  # optional
    database_url = os.getenv("DATABASE_URL", "")

    docker_client = docker.from_env()

    # Minimal in-memory state (dev). For prod, persist in Postgres.
    state: dict[str, dict[str, Any]] = {}

    def bot_dir(bot_id: str) -> Path:
        return config_root / bot_id

    def bot_config_path(bot_id: str) -> Path:
        return bot_dir(bot_id) / "config.json"

    def container_name(bot_id: str) -> str:
        return f"bot-{bot_id}"

    def image_name(runtime_version: str) -> str:
        return f"{image_repo}:{runtime_version}"

    def ensure_dirs(bot_id: str) -> None:
        bot_dir(bot_id).mkdir(parents=True, exist_ok=True)

    def write_config(bot_id: str, config: dict[str, Any]) -> None:
        import json

        ensure_dirs(bot_id)
        path = bot_config_path(bot_id)
        path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    def set_state(bot_id: str, status: str, **extra: Any) -> None:
        state.setdefault(bot_id, {})
        state[bot_id].update(
            {
                "bot_id": bot_id,
                "status": status,
                "updated_at": utc_now(),
                **extra,
            }
        )

    def get_state(bot_id: str) -> dict[str, Any]:
        if bot_id in state:
            return state[bot_id]
        # Attempt to infer from docker if state not present (best-effort)
        try:
            c = docker_client.containers.get(container_name(bot_id))
            return {
                "bot_id": bot_id,
                "status": "running" if c.status == "running" else "stopped",
                "container_id": c.id,
                "image": c.image.tags[0] if c.image.tags else None,
                "updated_at": utc_now(),
            }
        except NotFound:
            raise HTTPException(status_code=404, detail="bot not found")

    def start_container(bot_id: str, owner_id: str, runtime_version: str) -> docker.models.containers.Container:
        cfg_host_dir = str(bot_dir(bot_id).resolve())
        cfg_container_dir = "/bot/config"

        env = {
            "BOT_ID": bot_id,
            "BOT_OWNER_ID": owner_id,
            "BOT_CONFIG_PATH": f"{cfg_container_dir}/config.json",
        }
        if database_url:
            env["DATABASE_URL"] = database_url

        kwargs: dict[str, Any] = {
            "name": container_name(bot_id),
            "image": image_name(runtime_version),
            "detach": True,
            "restart_policy": {"Name": "unless-stopped"},
            "environment": env,
            "volumes": {cfg_host_dir: {"bind": cfg_container_dir, "mode": "ro"}},
            "labels": {
                "hf.bot_id": bot_id,
                "hf.owner_id": owner_id,
                "hf.runtime_version": runtime_version,
            },
        }
        if network_name:
            kwargs["network"] = network_name

        return docker_client.containers.run(**kwargs)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.post("/internal/v1/bots", response_model=BotCreateResponse, status_code=201)
    async def create_bot(req: BotCreateRequest) -> BotCreateResponse:
        bot_id = f"b_{uuid.uuid4().hex}"

        set_state(bot_id, "creating")
        try:
            write_config(bot_id, req.config)
            set_state(bot_id, "starting_container")

            # If container name already exists (unlikely for new bot_id), fail fast.
            try:
                docker_client.containers.get(container_name(bot_id))
                raise HTTPException(status_code=409, detail="container already exists")
            except NotFound:
                pass

            c = start_container(bot_id, req.owner_id, req.runtime_version)

            # Mark running optimistically; real prod should verify health/heartbeat.
            set_state(bot_id, "running", container_id=c.id, image=image_name(req.runtime_version))
            return BotCreateResponse(bot_id=bot_id, status="running")
        except HTTPException:
            raise
        except Exception as e:
            set_state(bot_id, "failed", reason=str(e))
            return BotCreateResponse(bot_id=bot_id, status="failed", reason=str(e))

    @app.get("/internal/v1/bots/{bot_id}", response_model=BotStatusResponse)
    async def bot_status(bot_id: str) -> BotStatusResponse:
        s = get_state(bot_id)
        return BotStatusResponse(**s)

    @app.post("/internal/v1/bots/{bot_id}/stop", response_model=BotStatusResponse)
    async def stop_bot(bot_id: str) -> BotStatusResponse:
        try:
            c = docker_client.containers.get(container_name(bot_id))
            c.stop(timeout=10)
            set_state(bot_id, "stopped", container_id=c.id, image=c.image.tags[0] if c.image.tags else None)
        except NotFound:
            raise HTTPException(status_code=404, detail="bot not found")
        except Exception as e:
            set_state(bot_id, "failed", reason=str(e))
        s = get_state(bot_id)
        return BotStatusResponse(**s)

    @app.post("/internal/v1/bots/{bot_id}/start", response_model=BotStatusResponse)
    async def start_bot(bot_id: str) -> BotStatusResponse:
        # In this minimal version we assume the container exists and just start it.
        try:
            c = docker_client.containers.get(container_name(bot_id))
            c.start()
            set_state(bot_id, "running", container_id=c.id, image=c.image.tags[0] if c.image.tags else None)
        except NotFound:
            raise HTTPException(status_code=404, detail="bot not found")
        except Exception as e:
            set_state(bot_id, "failed", reason=str(e))
        s = get_state(bot_id)
        return BotStatusResponse(**s)

    @app.put("/internal/v1/bots/{bot_id}/config", response_model=BotStatusResponse)
    async def update_bot_config(bot_id: str, req: BotConfigUpdateRequest, restart: bool = True) -> BotStatusResponse:
        s = get_state(bot_id)
        if s["status"] == "failed":
            raise HTTPException(status_code=409, detail="bot is failed; cannot update config")

        try:
            write_config(bot_id, req.config)

            if restart:
                try:
                    c = docker_client.containers.get(container_name(bot_id))
                    c.restart(timeout=10)
                    set_state(bot_id, "running", container_id=c.id, image=c.image.tags[0] if c.image.tags else None)
                except NotFound:
                    raise HTTPException(status_code=404, detail="bot not found")
        except HTTPException:
            raise
        except Exception as e:
            set_state(bot_id, "failed", reason=str(e))

        s2 = get_state(bot_id)
        return BotStatusResponse(**s2)

    return app


app = create_app()
