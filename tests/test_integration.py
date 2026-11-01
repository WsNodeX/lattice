"""Integration tests exercising several structures together."""

from __future__ import annotations

import unittest

from lattice import BloomFilter, CountMinSketch, HyperLogLog, MinHash, MinHashLSH


def _shingles(text: str, k: int = 3) -> set:
    words = text.lower().split()
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}


class TestNearDuplicatePipeline(unittest.TestCase):
    def test_lsh_finds_near_duplicates(self):
        docs = {
            "a": "the quick brown fox jumps over the lazy dog",
            "b": "the quick brown fox jumps over the lazy dog",  # exact dup
            "c": "a quick brown fox jumps over a lazy dog that rests",  # near dup
            "d": "completely unrelated text about databases and indexing",  # different
        }
        num_perm = 128
        lsh = MinHashLSH(threshold=0.5, num_perm=num_perm)
        sigs = {}
        for key, text in docs.items():
            mh = MinHash(num_perm=num_perm)
            mh.update_batch(_shingles(text))
            sigs[key] = mh
            lsh.insert(key, mh)

        candidates = lsh.query(sigs["a"])
        self.assertIn("a", candidates)
        self.assertIn("b", candidates)  # exact duplicate must collide
        self.assertNotIn("d", candidates)  # unrelated must not collide


class TestStreamAnalyticsPipeline(unittest.TestCase):
    def test_combined_structures(self):
        seen = BloomFilter(capacity=10000, false_positive_rate=0.01)
        freq = CountMinSketch(width=512, depth=5)
        unique = HyperLogLog(p=12)

        events = ["click", "view", "click", "purchase", "view", "click"]
        for ev in events:
            seen.add(ev)
            freq.add(ev)
            unique.add(ev)

        # every event was "seen"
        for ev in set(events):
            self.assertTrue(seen.contains(ev))
        # frequency lower bound respected
        self.assertGreaterEqual(freq.estimate("click"), 3)
        # distinct events: click, view, purchase -> 3
        self.assertLess(abs(unique.count() - 3), 1.5)


if __name__ == "__main__":
    unittest.main()
