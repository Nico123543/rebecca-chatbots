from __future__ import annotations

import unittest

from backend.app.influence import InfluenceEngine
from backend.app.models import InfluenceConfig


class InfluenceEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = InfluenceEngine(InfluenceConfig(max_packets_per_turn=1))

    def test_normalize_collapses_whitespace(self) -> None:
        normalized = self.engine.normalize("  too   many\nspaces\tinside   ")
        self.assertEqual(normalized, "too many spaces inside")

    def test_injection_count_scales_between_one_and_three(self) -> None:
        self.assertEqual(self.engine.injection_count("short fragment"), 1)
        self.assertEqual(
            self.engine.injection_count("this fragment has enough words to be injected twice"),
            2,
        )
        self.assertEqual(
            self.engine.injection_count(
                "this is a longer fragment with enough words to stay active across three turns in the loop"
            ),
            3,
        )


if __name__ == "__main__":
    unittest.main()
