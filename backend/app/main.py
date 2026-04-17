from __future__ import annotations

from pathlib import Path

from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import load_config, load_env
from .controller import SessionController
from .database import SQLiteStore
from .models import serialize


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = ROOT / "frontend" / "dist"


def create_app() -> FastAPI:
    load_env(ROOT / ".env")
    config = load_config(ROOT / "config.yaml")
    store = SQLiteStore(str(ROOT / config.storage.database_path))
    controller = SessionController(config, store)

    app = FastAPI(title="LLM Kiosk Installation")
    app.state.config = config
    app.state.controller = controller

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/api/health")
    async def health() -> dict:
        snapshot = controller.get_current_snapshot()
        return {
            "ok": True,
            "active_session_id": snapshot.session.id if snapshot.session else None,
            "status": serialize(snapshot.session.status) if snapshot.session else "idle",
        }

    @app.get("/api/config")
    async def get_config() -> dict:
        return config.public_dict()

    @app.get("/api/session/current")
    async def current_session() -> dict:
        return serialize(controller.get_current_snapshot())

    @app.post("/api/session/start")
    async def start_session() -> dict:
        snapshot = await controller.start_session()
        return serialize(snapshot)

    @app.post("/api/session/pause")
    async def pause_session() -> dict:
        try:
            snapshot = await controller.pause_session()
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return serialize(snapshot)

    @app.post("/api/session/resume")
    async def resume_session() -> dict:
        try:
            snapshot = await controller.resume_session()
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return serialize(snapshot)

    @app.post("/api/session/stop")
    async def stop_session() -> dict:
        try:
            snapshot = await controller.stop_session()
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return serialize(snapshot)

    @app.post("/api/fragments")
    async def add_fragment(request: Request) -> dict:
        body = await request.json()
        raw_text = str(body.get("rawText", "")).strip()
        if not raw_text:
            raise HTTPException(status_code=400, detail="rawText is required")
        try:
            snapshot = await controller.submit_fragment(raw_text)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return serialize(snapshot)

    @app.websocket("/api/session/{session_id}/stream")
    async def session_stream(session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        queue = await controller.event_bus.subscribe(session_id)
        try:
            while True:
                message = await queue.get()
                await websocket.send_json(message)
        except WebSocketDisconnect:
            await controller.event_bus.unsubscribe(session_id, queue)

    @app.get("/{full_path:path}", response_model=None)
    async def frontend(full_path: str) -> Any:
        if not FRONTEND_DIST.exists():
            return {"message": "Frontend build not found. Run npm install && npm run build in /frontend."}
        target = FRONTEND_DIST / full_path
        if full_path and target.exists() and target.is_file():
            return FileResponse(target)
        return FileResponse(FRONTEND_DIST / "index.html")

    return app


app = create_app()
