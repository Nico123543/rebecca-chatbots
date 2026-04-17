from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Protocol
from urllib import error, request

from .models import ModelConfig, PromptTurn, TurnRequest, TurnResponse


class ModelAdapter(Protocol):
    async def generate(self, payload: TurnRequest) -> TurnResponse:
        ...


def _compose_prompt(payload: TurnRequest) -> str:
    recent = "\n".join(
        f"{turn.speaker}: {turn.visible_text}" for turn in payload.recent_turns[-8:]
    )
    influence = "\n".join(packet.instructions for packet in payload.influence_packets)
    return "\n\n".join(
        chunk
        for chunk in [
            payload.model.system_prompt.strip(),
            f"Conversation summary:\n{payload.conversation_summary}".strip(),
            f"Recent turns:\n{recent}".strip(),
            f"Visitor influence:\n{influence}".strip(),
            f"Speaker for next turn: {payload.speaker}",
            "Respond in 2-4 sentences. Stay reflective and keep the loop alive.",
        ]
        if chunk
    )


def _compose_messages(payload: TurnRequest) -> list[dict[str, str]]:
    prompt = _compose_prompt(payload)
    return [
        {"role": "system", "content": payload.model.system_prompt.strip()},
        {"role": "user", "content": prompt},
    ]


class MockAdapter:
    def __init__(self, config: ModelConfig):
        self.config = config

    async def generate(self, payload: TurnRequest) -> TurnResponse:
        started = time.perf_counter()
        recent_focus = payload.recent_turns[-1].visible_text if payload.recent_turns else "silence"
        influence = payload.influence_packets[0].text if payload.influence_packets else ""
        prefix = "I keep noticing" if payload.speaker == "agent_a" else "What returns to me is"
        body = f"{prefix} how {recent_focus[:90].lower()} keeps reshaping the room."
        if influence:
            body += f" A visitor trace pulls the exchange toward '{influence[:60]}'."
        body += " We answer each other, but the answer never quite settles."
        elapsed = int((time.perf_counter() - started) * 1000)
        return TurnResponse(
            visible_text=body,
            raw_text=body,
            latency_ms=max(elapsed, 1),
            token_usage=len(body.split()),
        )


class OpenAICompatibleAdapter:
    def __init__(self, config: ModelConfig):
        self.config = config

    async def generate(self, payload: TurnRequest) -> TurnResponse:
        started = time.perf_counter()
        provider = self.config.provider.lower()
        default_endpoint = os.getenv("OPENAI_BASE_URL", "")
        if provider == "openrouter":
            default_endpoint = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        if provider == "lmstudio":
            default_endpoint = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
        endpoint = (self.config.endpoint or default_endpoint).rstrip("/")
        if not endpoint:
            raise RuntimeError(f"No endpoint configured for model {self.config.name}")
        url = f"{endpoint}/chat/completions"
        headers = {"Content-Type": "application/json"}
        api_key_env = self.config.api_key_env or "OPENAI_API_KEY"
        api_key = os.getenv(api_key_env)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        if provider == "openrouter":
            headers["HTTP-Referer"] = os.getenv("OPENROUTER_SITE_URL", "http://localhost")
            headers["X-Title"] = os.getenv("OPENROUTER_APP_NAME", "Reciprocal Drift")
        payload_body = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "messages": _compose_messages(payload),
        }
        try:
            body = await asyncio.to_thread(
                _post_json,
                url,
                headers,
                payload_body,
                30,
            )
        except error.HTTPError as exc:  # pragma: no cover - network path
            raise RuntimeError(exc.read().decode("utf-8")) from exc
        except error.URLError as exc:  # pragma: no cover - network path
            raise RuntimeError(str(exc.reason)) from exc
        content = body["choices"][0]["message"]["content"].strip()
        usage = body.get("usage", {}).get("total_tokens")
        elapsed = int((time.perf_counter() - started) * 1000)
        return TurnResponse(
            visible_text=content,
            raw_text=content,
            latency_ms=max(elapsed, 1),
            token_usage=usage,
        )


class OllamaAdapter:
    def __init__(self, config: ModelConfig):
        self.config = config

    async def generate(self, payload: TurnRequest) -> TurnResponse:
        started = time.perf_counter()
        endpoint = (self.config.endpoint or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/api")).rstrip("/")
        url = f"{endpoint}/chat"
        payload_body = {
            "model": self.config.model,
            "stream": False,
            "messages": _compose_messages(payload),
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }
        headers = {"Content-Type": "application/json"}
        try:
            body = await asyncio.to_thread(
                _post_json,
                url,
                headers,
                payload_body,
                30,
            )
        except error.HTTPError as exc:  # pragma: no cover - live path
            raise RuntimeError(exc.read().decode("utf-8")) from exc
        except error.URLError as exc:  # pragma: no cover - live path
            raise RuntimeError(str(exc.reason)) from exc
        content = body.get("message", {}).get("content", "").strip()
        elapsed = int((time.perf_counter() - started) * 1000)
        prompt_eval = body.get("prompt_eval_count") or 0
        eval_count = body.get("eval_count") or 0
        return TurnResponse(
            visible_text=content,
            raw_text=content,
            latency_ms=max(elapsed, 1),
            token_usage=prompt_eval + eval_count or None,
        )


def _post_json(url: str, headers: dict[str, str], payload_body: dict, timeout: int) -> dict:
    data = json.dumps(payload_body).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method="POST")
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def create_adapter(config: ModelConfig) -> ModelAdapter:
    provider = config.provider.lower()
    if provider == "mock":
        return MockAdapter(config)
    if provider in {"openai", "openai-compatible", "local-http", "openrouter", "lmstudio"}:
        return OpenAICompatibleAdapter(config)
    if provider == "ollama":
        return OllamaAdapter(config)
    raise ValueError(f"Unsupported provider: {config.provider}")
