from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from backend.app.controller import SessionController
from backend.app.database import SQLiteStore
from backend.app.models import (
    ConversationConfig,
    InfluenceConfig,
    ModelConfig,
    RetryConfig,
    RuntimeConfig,
    SessionStatus,
    StorageConfig,
    UIConfig,
)


def make_config(tmp_path: Path) -> RuntimeConfig:
    return RuntimeConfig(
        model_mode="local",
        ui=UIConfig(title="Test", subtitle="Test"),
        conversation=ConversationConfig(
            delay_seconds=0.01,
            context_turn_window=4,
            summary_character_limit=300,
        ),
        retry=RetryConfig(attempts=1, backoff_seconds=0.01, timeout_seconds=1.0),
        influence=InfluenceConfig(max_packets_per_turn=1),
        storage=StorageConfig(
            database_path=str(tmp_path / "kiosk.sqlite3"),
            export_dir=str(tmp_path / "exports"),
        ),
        models={
            "agent_a": ModelConfig(
                name="Agent A",
                provider="mock",
                model="mirror-a",
                system_prompt="Speak in reflective English.",
            ),
            "agent_b": ModelConfig(
                name="Agent B",
                provider="mock",
                model="mirror-b",
                system_prompt="Reply in reflective English.",
            ),
        },
    )


class SessionControllerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        tmp_path = Path(self.tempdir.name)
        self.config = make_config(tmp_path)
        self.store = SQLiteStore(self.config.storage.database_path)
        self.controller = SessionController(self.config, self.store)

    async def asyncTearDown(self) -> None:
        if self.controller.current_session_id:
            snapshot = self.controller.get_current_snapshot()
            if snapshot.session and snapshot.session.status not in {SessionStatus.STOPPED, SessionStatus.ERROR}:
                await self.controller.stop_session()
        self.tempdir.cleanup()

    async def test_session_generates_turns_and_applies_fragment(self) -> None:
        snapshot = await self.controller.start_session()
        self.assertIsNotNone(snapshot.session)

        await asyncio.sleep(0.06)
        snapshot = self.controller.get_current_snapshot()
        self.assertGreaterEqual(len(snapshot.turns), 2)

        await self.controller.submit_fragment("Hold the feeling of an almost-confession.")
        await asyncio.sleep(0.08)
        snapshot = self.controller.get_current_snapshot()

        self.assertTrue(snapshot.fragments)
        self.assertTrue(any(fragment.times_used > 0 for fragment in snapshot.fragments))
        self.assertTrue(any(turn.influence_ids for turn in snapshot.turns))

    async def test_pause_and_resume_change_session_status(self) -> None:
        await self.controller.start_session()
        paused = await self.controller.pause_session()
        self.assertEqual(paused.session.status, SessionStatus.PAUSED)

        resumed = await self.controller.resume_session()
        self.assertEqual(resumed.session.status, SessionStatus.RUNNING)


if __name__ == "__main__":
    unittest.main()
