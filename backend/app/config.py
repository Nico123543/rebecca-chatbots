from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .models import (
    ConversationConfig,
    InfluenceConfig,
    ModelConfig,
    RetryConfig,
    RuntimeConfig,
    StorageConfig,
    UIConfig,
)


def load_env(env_path: str | Path = ".env") -> None:
    path = Path(env_path)
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _yaml_load(config_path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised once dependencies are installed
        raise RuntimeError("PyYAML is required to load config.yaml") from exc
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("config.yaml must contain a top-level mapping")
    return data


def _build_model_config(raw: dict[str, Any], fallback_name: str) -> ModelConfig:
    return ModelConfig(
        name=str(raw.get("name", fallback_name)),
        provider=str(raw.get("provider", "mock")),
        model=str(raw.get("model", fallback_name.lower().replace(" ", "-"))),
        system_prompt=str(raw.get("system_prompt", "")).strip(),
        endpoint=raw.get("endpoint"),
        api_key_env=raw.get("api_key_env"),
        temperature=float(raw.get("temperature", 0.9)),
        max_tokens=int(raw.get("max_tokens", 220)),
    )


def _resolve_model_mode(raw: dict[str, Any]) -> str:
    runtime = raw.get("runtime", {})
    configured = str(runtime.get("model_mode", "local")).strip().lower()
    override = os.getenv("KIOSK_MODEL_MODE", configured).strip().lower()
    if override not in {"local", "online"}:
        raise ValueError("KIOSK_MODEL_MODE must be either 'local' or 'online'")
    return override


def _resolve_models(raw: dict[str, Any], mode: str) -> dict[str, Any]:
    model_profiles = raw.get("model_profiles")
    if isinstance(model_profiles, dict):
        selected = model_profiles.get(mode)
        if not isinstance(selected, dict):
            raise ValueError(f"config.yaml is missing model_profiles.{mode}")
        return selected
    return raw.get("models", {})


def load_config(config_path: str | Path = "config.yaml") -> RuntimeConfig:
    path = Path(config_path)
    raw = _yaml_load(path) if path.exists() else {}

    model_mode = _resolve_model_mode(raw)
    ui = raw.get("ui", {})
    conversation = raw.get("conversation", {})
    retry = raw.get("retry", {})
    influence = raw.get("influence", {})
    storage = raw.get("storage", {})
    models = _resolve_models(raw, model_mode)

    model_configs = {
        "agent_a": _build_model_config(models.get("agent_a", {}), "Agent A"),
        "agent_b": _build_model_config(models.get("agent_b", {}), "Agent B"),
    }

    return RuntimeConfig(
        model_mode=model_mode,
        ui=UIConfig(
            title=str(ui.get("title", "Reciprocal Drift")),
            subtitle=str(ui.get("subtitle", "A local installation where two LLMs orbit each other.")),
        ),
        conversation=ConversationConfig(
            delay_seconds=float(conversation.get("delay_seconds", 3.0)),
            context_turn_window=int(conversation.get("context_turn_window", 10)),
            summary_character_limit=int(conversation.get("summary_character_limit", 1200)),
            default_language=str(conversation.get("default_language", "en")),
        ),
        retry=RetryConfig(
            attempts=int(retry.get("attempts", 2)),
            backoff_seconds=float(retry.get("backoff_seconds", 1.0)),
            timeout_seconds=float(retry.get("timeout_seconds", 20.0)),
        ),
        influence=InfluenceConfig(
            max_packets_per_turn=int(influence.get("max_packets_per_turn", 1))
        ),
        storage=StorageConfig(
            database_path=str(storage.get("database_path", "data/kiosk.sqlite3")),
            export_dir=str(storage.get("export_dir", "data/exports")),
        ),
        models=model_configs,
    )
