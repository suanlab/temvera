from datetime import datetime, timezone
import unittest

from temvera.generator import generate_lifecycle_suite
from temvera.index import LexicalIndex
from temvera.oracle import LifecycleOracle
from temvera.retrieval import build_packet


class RetrievalTest(unittest.TestCase):
    def test_packet_carries_sources_authority_and_validity(self) -> None:
        state = LifecycleOracle(generate_lifecycle_suite(seed=2)).state_as_of(
            datetime(2025, 1, 10, tzinfo=timezone.utc)
        )
        packet = build_packet(LexicalIndex(state.values()), "agent owner")
        self.assertTrue(packet.items)
        self.assertEqual(packet.provenance_coverage, 1.0)
        self.assertTrue(all(item.source_ids for item in packet.items))
        self.assertTrue(all(item.authority for item in packet.items))


if __name__ == "__main__":
    unittest.main()
