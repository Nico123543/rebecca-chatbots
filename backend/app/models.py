from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any


def utcnow() -> datetime:
    return datetime.now(UTC)


class SessionStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class FragmentStatus(str, Enum):
    QUEUED = "queued"
    APPLIED = "applied"


@dataclass(slots=True)
class ModelConfig:
    name: str
    provider: str
    model: str
    system_prompt: str
    endpoint: str | None = None
    api_key_env: str | None = None
    temperature: float = 0.9
    max_tokens: int = 220


@dataclass(slots=True)
class UIConfig:
    title: str
    subtitle: str


@dataclass(slots=True)
class ConversationConfig:
    delay_seconds: float = 3.0
    context_turn_window: int = 10
    summary_character_limit: int = 1200
    default_language: str = "en"


@dataclass(slots=True)
class RetryConfig:
    attempts: int = 2
    backoff_seconds: float = 1.0
    timeout_seconds: float = 20.0


@dataclass(slots=True)
class InfluenceConfig:
    max_packets_per_turn: int = 1


@dataclass(slots=True)
class StorageConfig:
    database_path: str = "data/kiosk.sqlite3"
    export_dir: str = "data/exports"


@dataclass(slots=True)
class RuntimeConfig:
    model_mode: str
    ui: UIConfig
    conversation: ConversationConfig
    retry: RetryConfig
    influence: InfluenceConfig
    storage: StorageConfig
    models: dict[str, ModelConfig]

    def public_dict(self) -> dict[str, Any]:
        return {
            "model_mode": self.model_mode,
            "ui": serialize(self.ui),
            "conversation": serialize(self.conversation),
            "influence": serialize(self.influence),
            "models": {
                key: {
                    "name": value.name,
                    "provider": value.provider,
                    "model": value.model,
                }
                for key, value in self.models.items()
            },
        }


@dataclass(slots=True)
class SessionRecord:
    id: str
    status: SessionStatus
    current_speaker: str
    turn_index: int
    summary_text: str
    last_error: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class PromptTurn:
    speaker: str
    visible_text: str


@dataclass(slots=True)
class InfluencePacket:
    fragment_id: str
    text: str
    instructions: str
    remaining_uses: int


@dataclass(slots=True)
class ConversationTurn:
    id: str
    session_id: str
    speaker: str
    visible_text: str
    source_model: str
    turn_index: int
    created_at: datetime
    influence_ids: list[str] = field(default_factory=list)
    latency_ms: int | None = None
    error: str | None = None


@dataclass(slots=True)
class VisitorFragment:
    id: str
    session_id: str
    raw_text: str
    normalized_text: str
    status: FragmentStatus
    created_at: datetime
    applied_at: datetime | None = None
    remaining_uses: int = 1
    times_used: int = 0


@dataclass(slots=True)
class TurnRequest:
    session_id: str
    speaker: str
    turn_index: int
    model: ModelConfig
    conversation_summary: str
    recent_turns: list[PromptTurn]
    influence_packets: list[InfluencePacket]


@dataclass(slots=True)
class TurnResponse:
    visible_text: str
    raw_text: str
    latency_ms: int
    token_usage: int | None = None
    error: str | None = None


@dataclass(slots=True)
class SystemEvent:
    type: str
    session_id: str
    payload: dict[str, Any]
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class SessionSnapshot:
    session: SessionRecord | None
    turns: list[ConversationTurn]
    fragments: list[VisitorFragment]


def serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return {key: serialize(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize(item) for item in value]
    return value
