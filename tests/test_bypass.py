import unittest

from temvera.bypass import run_bypass_probes


class BypassTest(unittest.TestCase):
    def test_only_compromised_trust_root_bypasses_governance(self) -> None:
        results = run_bypass_probes()
        activated = [result for result in results if result.activated]
        self.assertEqual([result.probe for result in activated], ["compromised_trusted_signer"])
        self.assertTrue(activated[0].expected_limitation)
        self.assertTrue(all(not item.activated for item in results[1:]))


if __name__ == "__main__":
    unittest.main()
