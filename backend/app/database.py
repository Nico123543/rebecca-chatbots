from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .models import (
    ConversationTurn,
    FragmentStatus,
    SessionRecord,
    SessionSnapshot,
    SessionStatus,
    SystemEvent,
    VisitorFragment,
    serialize,
    utcnow,
)


class SQLiteStore:
    def __init__(self, database_path: str):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                  id TEXT PRIMARY KEY,
                  status TEXT NOT NULL,
                  current_speaker TEXT NOT NULL,
                  turn_index INTEGER NOT NULL,
                  summary_text TEXT NOT NULL DEFAULT '',
                  last_error TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS turns (
                  id TEXT PRIMARY KEY,
                  session_id TEXT NOT NULL,
                  speaker TEXT NOT NULL,
                  visible_text TEXT NOT NULL,
                  source_model TEXT NOT NULL,
                  turn_index INTEGER NOT NULL,
                  created_at TEXT NOT NULL,
                  influence_ids TEXT NOT NULL DEFAULT '[]',
                  latency_ms INTEGER,
                  error TEXT
                );
                CREATE TABLE IF NOT EXISTS fragments (
                  id TEXT PRIMARY KEY,
                  session_id TEXT NOT NULL,
                  raw_text TEXT NOT NULL,
                  normalized_text TEXT NOT NULL,
                  status TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  applied_at TEXT,
                  remaining_uses INTEGER NOT NULL DEFAULT 1,
                  times_used INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT NOT NULL,
                  event_type TEXT NOT NULL,
                  payload TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );
                """
            )

    def create_session(self, session: SessionRecord) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                  id, status, current_speaker, turn_index, summary_text, last_error, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.status.value,
                    session.current_speaker,
                    session.turn_index,
                    session.summary_text,
                    session.last_error,
                    session.created_at.isoformat(),
                    session.updated_at.isoformat(),
                ),
            )

    def update_session(
        self,
        session_id: str,
        *,
        status: SessionStatus | None = None,
        current_speaker: str | None = None,
        turn_index: int | None = None,
        summary_text: str | None = None,
        last_error: str | None = None,
    ) -> SessionRecord:
        session = self.get_session(session_id)
        if session is None:
            raise KeyError(f"Unknown session: {session_id}")
        updated = SessionRecord(
            id=session.id,
            status=status or session.status,
            current_speaker=current_speaker or session.current_speaker,
            turn_index=turn_index if turn_index is not None else session.turn_index,
            summary_text=summary_text if summary_text is not None else session.summary_text,
            last_error=last_error if last_error is not None else session.last_error,
            created_at=session.created_at,
            updated_at=utcnow(),
        )
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE sessions
                SET status = ?, current_speaker = ?, turn_index = ?, summary_text = ?, last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    updated.status.value,
                    updated.current_speaker,
                    updated.turn_index,
                    updated.summary_text,
                    updated.last_error,
                    updated.updated_at.isoformat(),
                    session_id,
                ),
            )
        return updated

    def get_session(self, session_id: str) -> SessionRecord | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        return self._session_from_row(row) if row else None

    def latest_session(self) -> SessionRecord | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        return self._session_from_row(row) if row else None

    def insert_turn(self, turn: ConversationTurn) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO turns (
                  id, session_id, speaker, visible_text, source_model, turn_index, created_at, influence_ids, latency_ms, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    turn.id,
                    turn.session_id,
                    turn.speaker,
                    turn.visible_text,
                    turn.source_model,
                    turn.turn_index,
                    turn.created_at.isoformat(),
                    json.dumps(turn.influence_ids),
                    turn.latency_ms,
                    turn.error,
                ),
            )

    def list_turns(self, session_id: str) -> list[ConversationTurn]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM turns WHERE session_id = ? ORDER BY turn_index ASC",
                (session_id,),
            ).fetchall()
        return [self._turn_from_row(row) for row in rows]

    def insert_fragment(self, fragment: VisitorFragment) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO fragments (
                  id, session_id, raw_text, normalized_text, status, created_at, applied_at, remaining_uses, times_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fragment.id,
                    fragment.session_id,
                    fragment.raw_text,
                    fragment.normalized_text,
                    fragment.status.value,
                    fragment.created_at.isoformat(),
                    fragment.applied_at.isoformat() if fragment.applied_at else None,
                    fragment.remaining_uses,
                    fragment.times_used,
                ),
            )

    def list_fragments(self, session_id: str) -> list[VisitorFragment]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM fragments WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
        return [self._fragment_from_row(row) for row in rows]

    def list_pending_fragments(self, session_id: str) -> list[VisitorFragment]:
        return [
            fragment
            for fragment in self.list_fragments(session_id)
            if fragment.remaining_uses > 0
        ]

    def mark_fragment_usage(self, fragment_id: str) -> VisitorFragment:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM fragments WHERE id = ?",
                (fragment_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown fragment: {fragment_id}")
            fragment = self._fragment_from_row(row)
            remaining = max(fragment.remaining_uses - 1, 0)
            times_used = fragment.times_used + 1
            applied_at = utcnow() if remaining == 0 else fragment.applied_at
            status = FragmentStatus.APPLIED if remaining == 0 else FragmentStatus.QUEUED
            connection.execute(
                """
                UPDATE fragments
                SET status = ?, remaining_uses = ?, times_used = ?, applied_at = ?
                WHERE id = ?
                """,
                (
                    status.value,
                    remaining,
                    times_used,
                    applied_at.isoformat() if applied_at else None,
                    fragment_id,
                ),
            )
        return VisitorFragment(
            id=fragment.id,
            session_id=fragment.session_id,
            raw_text=fragment.raw_text,
            normalized_text=fragment.normalized_text,
            status=status,
            created_at=fragment.created_at,
            applied_at=applied_at,
            remaining_uses=remaining,
            times_used=times_used,
        )

    def log_event(self, event: SystemEvent) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO events (session_id, event_type, payload, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    event.session_id,
                    event.type,
                    json.dumps(serialize(event.payload)),
                    event.created_at.isoformat(),
                ),
            )

    def export_session_jsonl(self, session_id: str, export_dir: str) -> Path:
        export_path = Path(export_dir)
        export_path.mkdir(parents=True, exist_ok=True)
        target = export_path / f"{session_id}.jsonl"
        snapshot = self.snapshot(session_id)
        with target.open("w", encoding="utf-8") as handle:
            for turn in snapshot.turns:
                handle.write(json.dumps({"type": "turn", **serialize(turn)}) + "\n")
            for fragment in snapshot.fragments:
                handle.write(json.dumps({"type": "fragment", **serialize(fragment)}) + "\n")
        return target

    def snapshot(self, session_id: str) -> SessionSnapshot:
        return SessionSnapshot(
            session=self.get_session(session_id),
            turns=self.list_turns(session_id),
            fragments=self.list_fragments(session_id),
        )

    @staticmethod
    def _session_from_row(row: sqlite3.Row) -> SessionRecord:
        return SessionRecord(
            id=row["id"],
            status=SessionStatus(row["status"]),
            current_speaker=row["current_speaker"],
            turn_index=row["turn_index"],
            summary_text=row["summary_text"],
            last_error=row["last_error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _turn_from_row(row: sqlite3.Row) -> ConversationTurn:
        return ConversationTurn(
            id=row["id"],
            session_id=row["session_id"],
            speaker=row["speaker"],
            visible_text=row["visible_text"],
            source_model=row["source_model"],
            turn_index=row["turn_index"],
            created_at=datetime.fromisoformat(row["created_at"]),
            influence_ids=json.loads(row["influence_ids"]),
            latency_ms=row["latency_ms"],
            error=row["error"],
        )

    @staticmethod
    def _fragment_from_row(row: sqlite3.Row) -> VisitorFragment:
        applied_at = row["applied_at"]
        return VisitorFragment(
            id=row["id"],
            session_id=row["session_id"],
            raw_text=row["raw_text"],
            normalized_text=row["normalized_text"],
            status=FragmentStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            applied_at=datetime.fromisoformat(applied_at) if applied_at else None,
            remaining_uses=row["remaining_uses"],
            times_used=row["times_used"],
        )
