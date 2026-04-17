from __future__ import annotations

import unittest

from backend.app.adapters import MockAdapter, OllamaAdapter, OpenAICompatibleAdapter, create_adapter
from backend.app.models import ModelConfig


class AdapterFactoryTests(unittest.TestCase):
    def test_create_openrouter_adapter(self) -> None:
        adapter = create_adapter(
            ModelConfig(
                name="Agent A / OpenRouter",
                provider="openrouter",
                model="google/gemma-3-4b-it:free",
                endpoint="https://openrouter.ai/api/v1",
                api_key_env="OPENROUTER_API_KEY",
                system_prompt="test",
            )
        )
        self.assertIsInstance(adapter, OpenAICompatibleAdapter)

    def test_create_lmstudio_adapter(self) -> None:
        adapter = create_adapter(
            ModelConfig(
                name="Agent B / LM Studio",
                provider="lmstudio",
                model="google/gemma-3-4b",
                endpoint="http://127.0.0.1:1234/v1",
                system_prompt="test",
            )
        )
        self.assertIsInstance(adapter, OpenAICompatibleAdapter)

    def test_create_ollama_adapter(self) -> None:
        adapter = create_adapter(
            ModelConfig(
                name="Agent B / Ollama",
                provider="ollama",
                model="tinyllama:latest",
                endpoint="http://127.0.0.1:11434/api",
                system_prompt="test",
            )
        )
        self.assertIsInstance(adapter, OllamaAdapter)

    def test_create_mock_adapter(self) -> None:
        adapter = create_adapter(
            ModelConfig(
                name="Mock",
                provider="mock",
                model="mock",
                system_prompt="test",
            )
        )
        self.assertIsInstance(adapter, MockAdapter)


if __name__ == "__main__":
    unittest.main()
