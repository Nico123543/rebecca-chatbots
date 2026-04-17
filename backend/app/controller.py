from __future__ import annotations

import asyncio
import uuid
from contextlib import suppress

from .adapters import ModelAdapter, create_adapter
from .database import SQLiteStore
from .influence import InfluenceEngine
from .models import (
    ConversationTurn,
    PromptTurn,
    RuntimeConfig,
    SessionRecord,
    SessionSnapshot,
    SessionStatus,
    SystemEvent,
    TurnRequest,
    serialize,
    utcnow,
)


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, session_id: str) -> asyncio.Queue[dict]:
        queue: asyncio.Queue[dict] = asyncio.Queue()
        async with self._lock:
            self._subscribers.setdefault(session_id, set()).add(queue)
        return queue

    async def unsubscribe(self, session_id: str, queue: asyncio.Queue[dict]) -> None:
        async with self._lock:
            listeners = self._subscribers.get(session_id)
            if not listeners:
                return
            listeners.discard(queue)
            if not listeners:
                self._subscribers.pop(session_id, None)

    async def publish(self, event: SystemEvent) -> None:
        async with self._lock:
            listeners = list(self._subscribers.get(event.session_id, set()))
        payload = serialize(event)
        for listener in listeners:
            await listener.put(payload)


class SessionController:
    def __init__(self, config: RuntimeConfig, store: SQLiteStore):
        self.config = config
        self.store = store
        self.influence = InfluenceEngine(config.influence)
        self.adapters: dict[str, ModelAdapter] = {
            "agent_a": create_adapter(config.models["agent_a"]),
            "agent_b": create_adapter(config.models["agent_b"]),
        }
        self.event_bus = EventBus()
        latest_session = store.latest_session()
        self.current_session_id: str | None = latest_session.id if latest_session else None
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    async def start_session(self) -> SessionSnapshot:
        async with self._lock:
            if self.current_session_id:
                await self._stop_current_session_locked()
            session = SessionRecord(
                id=str(uuid.uuid4()),
                status=SessionStatus.RUNNING,
                current_speaker="agent_a",
                turn_index=0,
                summary_text="",
                last_error=None,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            self.store.create_session(session)
            self.current_session_id = session.id
            self._task = asyncio.create_task(self._run_loop(session.id))
            await self._publish("session.started", session.id, {"session": serialize(session)})
            return self.store.snapshot(session.id)

    async def pause_session(self) -> SessionSnapshot:
        session = self._require_current_session()
        updated = self.store.update_session(session.id, status=SessionStatus.PAUSED)
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        self._task = None
        await self._publish("session.paused", session.id, {"session": serialize(updated)})
        return self.store.snapshot(session.id)

    async def resume_session(self) -> SessionSnapshot:
        session = self._require_current_session()
        updated = self.store.update_session(session.id, status=SessionStatus.RUNNING, last_error=None)
        self._task = asyncio.create_task(self._run_loop(session.id))
        await self._publish("session.resumed", session.id, {"session": serialize(updated)})
        return self.store.snapshot(session.id)

    async def stop_session(self) -> SessionSnapshot:
        session, updated = await self._stop_current_session_locked()
        await self._publish("session.stopped", session.id, {"session": serialize(updated)})
        return self.store.snapshot(session.id)

    async def submit_fragment(self, raw_text: str) -> SessionSnapshot:
        session = self._require_current_session()
        fragment = self.influence.create_fragment(session.id, raw_text)
        self.store.insert_fragment(fragment)
        await self._publish("fragment.queued", session.id, {"fragment": serialize(fragment)})
        return self.store.snapshot(session.id)

    def get_current_snapshot(self) -> SessionSnapshot:
        if not self.current_session_id:
            return SessionSnapshot(session=None, turns=[], fragments=[])
        return self.store.snapshot(self.current_session_id)

    async def _run_loop(self, session_id: str) -> None:
        try:
            while True:
                session = self.store.get_session(session_id)
                if session is None or session.status in {SessionStatus.STOPPED, SessionStatus.ERROR}:
                    return
                if session.status == SessionStatus.PAUSED:
                    await asyncio.sleep(0.1)
                    continue
                await self._step(session_id)
                await asyncio.sleep(self.config.conversation.delay_seconds)
        except asyncio.CancelledError:
            raise

    async def _step(self, session_id: str) -> None:
        session = self.store.get_session(session_id)
        if session is None:
            return
        speaker = "agent_a" if session.turn_index % 2 == 0 else "agent_b"
        model_config = self.config.models[speaker]
        turns = self.store.list_turns(session_id)
        summary_text = self._summarize(turns)
        if summary_text != session.summary_text:
            session = self.store.update_session(session_id, summary_text=summary_text)
        recent_turns = [
            PromptTurn(speaker=turn.speaker, visible_text=turn.visible_text)
            for turn in turns[-self.config.conversation.context_turn_window :]
        ]
        pending_fragments = self.store.list_pending_fragments(session_id)
        packets = self.influence.select_packets(pending_fragments)
        request = TurnRequest(
            session_id=session_id,
            speaker=speaker,
            turn_index=session.turn_index,
            model=model_config,
            conversation_summary=summary_text,
            recent_turns=recent_turns,
            influence_packets=packets,
        )

        try:
            response = await self._generate_with_retry(self.adapters[speaker], request)
        except Exception as exc:  # pragma: no cover - exercised by integration use
            message = str(exc)
            failed = self.store.update_session(
                session_id,
                status=SessionStatus.ERROR,
                last_error=message,
            )
            await self._publish("session.error", session_id, {"session": serialize(failed), "error": message})
            return

        turn = ConversationTurn(
            id=str(uuid.uuid4()),
            session_id=session_id,
            speaker=speaker,
            visible_text=response.visible_text,
            source_model=model_config.model,
            turn_index=session.turn_index,
            created_at=utcnow(),
            influence_ids=[packet.fragment_id for packet in packets],
            latency_ms=response.latency_ms,
            error=response.error,
        )
        self.store.insert_turn(turn)
        for packet in packets:
            fragment = self.store.mark_fragment_usage(packet.fragment_id)
            await self._publish("fragment.updated", session_id, {"fragment": serialize(fragment)})
        updated = self.store.update_session(
            session_id,
            turn_index=session.turn_index + 1,
            current_speaker="agent_b" if speaker == "agent_a" else "agent_a",
            last_error=None,
        )
        await self._publish(
            "turn.created",
            session_id,
            {"turn": serialize(turn), "session": serialize(updated)},
        )

    async def _generate_with_retry(self, adapter: ModelAdapter, payload: TurnRequest):
        last_error: Exception | None = None
        attempts = max(self.config.retry.attempts, 1)
        for attempt in range(1, attempts + 1):
            try:
                return await asyncio.wait_for(
                    adapter.generate(payload),
                    timeout=self.config.retry.timeout_seconds,
                )
            except Exception as exc:
                last_error = exc
                if attempt == attempts:
                    break
                await asyncio.sleep(self.config.retry.backoff_seconds)
        raise RuntimeError(str(last_error) if last_error else "Unknown adapter error")

    def _summarize(self, turns: list[ConversationTurn]) -> str:
        overflow = max(len(turns) - self.config.conversation.context_turn_window, 0)
        if overflow <= 0:
            return ""
        older_turns = turns[:overflow]
        summary = " ".join(
            f"{turn.speaker} noticed {turn.visible_text}" for turn in older_turns[-4:]
        )
        return summary[-self.config.conversation.summary_character_limit :]

    async def _publish(self, event_type: str, session_id: str, payload: dict) -> None:
        event = SystemEvent(type=event_type, session_id=session_id, payload=payload)
        self.store.log_event(event)
        await self.event_bus.publish(event)

    def _require_current_session(self) -> SessionRecord:
        if not self.current_session_id:
            raise RuntimeError("No active session. Start a session first.")
        session = self.store.get_session(self.current_session_id)
        if session is None:
            raise RuntimeError("Current session no longer exists.")
        return session

    async def _stop_current_session_locked(self) -> tuple[SessionRecord, SessionRecord]:
        session = self._require_current_session()
        updated = self.store.update_session(session.id, status=SessionStatus.STOPPED)
        self.store.export_session_jsonl(session.id, self.config.storage.export_dir)
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        self._task = None
        return session, updated
