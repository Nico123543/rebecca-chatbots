from __future__ import annotations

import re
import uuid

from .models import FragmentStatus, InfluenceConfig, InfluencePacket, VisitorFragment, utcnow


class InfluenceEngine:
    def __init__(self, config: InfluenceConfig):
        self.config = config

    def create_fragment(self, session_id: str, raw_text: str) -> VisitorFragment:
        normalized = self.normalize(raw_text)
        return VisitorFragment(
            id=str(uuid.uuid4()),
            session_id=session_id,
            raw_text=raw_text.strip(),
            normalized_text=normalized,
            status=FragmentStatus.QUEUED,
            created_at=utcnow(),
            remaining_uses=self.injection_count(normalized),
        )

    def normalize(self, raw_text: str) -> str:
        collapsed = re.sub(r"\s+", " ", raw_text).strip()
        return collapsed[:220]

    def injection_count(self, normalized_text: str) -> int:
        length = len(normalized_text.split())
        if length >= 16:
            return 3
        if length >= 8:
            return 2
        return 1

    def select_packets(self, fragments: list[VisitorFragment]) -> list[InfluencePacket]:
        chosen = fragments[: self.config.max_packets_per_turn]
        packets: list[InfluencePacket] = []
        for fragment in chosen:
            packets.append(
                InfluencePacket(
                    fragment_id=fragment.id,
                    text=fragment.normalized_text,
                    instructions=(
                        "Let this visitor fragment tint your response without quoting it verbatim: "
                        f"{fragment.normalized_text}"
                    ),
                    remaining_uses=fragment.remaining_uses,
                )
            )
        return packets

