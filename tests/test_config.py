from __future__ import annotations

import os
import tempfile
import textwrap
import unittest
from pathlib import Path

from backend.app.config import load_config


CONFIG_TEMPLATE = """
runtime:
  model_mode: "local"
ui:
  title: "Test"
  subtitle: "Test"
model_profiles:
  local:
    agent_a:
      name: "Local A"
      provider: "lmstudio"
      endpoint: "http://127.0.0.1:1234/v1"
      model: "local-a"
      system_prompt: "local a"
    agent_b:
      name: "Local B"
      provider: "lmstudio"
      endpoint: "http://127.0.0.1:1234/v1"
      model: "local-b"
      system_prompt: "local b"
  online:
    agent_a:
      name: "Online A"
      provider: "openrouter"
      endpoint: "https://openrouter.ai/api/v1"
      api_key_env: "OPENROUTER_API_KEY"
      model: "online-a"
      system_prompt: "online a"
    agent_b:
      name: "Online B"
      provider: "openrouter"
      endpoint: "https://openrouter.ai/api/v1"
      api_key_env: "OPENROUTER_API_KEY"
      model: "online-b"
      system_prompt: "online b"
"""


class ConfigTests(unittest.TestCase):
    def test_loads_default_local_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            config_path = Path(tempdir) / "config.yaml"
            config_path.write_text(textwrap.dedent(CONFIG_TEMPLATE), encoding="utf-8")
            config = load_config(config_path)
            self.assertEqual(config.model_mode, "local")
            self.assertEqual(config.models["agent_a"].provider, "lmstudio")
            self.assertEqual(config.models["agent_b"].model, "local-b")

    def test_environment_override_switches_to_online_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            config_path = Path(tempdir) / "config.yaml"
            config_path.write_text(textwrap.dedent(CONFIG_TEMPLATE), encoding="utf-8")
            previous = os.environ.get("KIOSK_MODEL_MODE")
            os.environ["KIOSK_MODEL_MODE"] = "online"
            try:
                config = load_config(config_path)
            finally:
                if previous is None:
                    os.environ.pop("KIOSK_MODEL_MODE", None)
                else:
                    os.environ["KIOSK_MODEL_MODE"] = previous
            self.assertEqual(config.model_mode, "online")
            self.assertEqual(config.models["agent_a"].provider, "openrouter")
            self.assertEqual(config.models["agent_b"].model, "online-b")


if __name__ == "__main__":
    unittest.main()
