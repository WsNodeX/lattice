"""Tests for BloomFilter."""

from __future__ import annotations

import unittest

from lattice import BloomFilter
from lattice.errors import IncompatibleFilterError


class TestBloomFilter(unittest.TestCase):
    def test_invalid_params(self):
        with self.assertRaises(ValueError):
            BloomFilter(capacity=0)
        with self.assertRaises(ValueError):
            BloomFilter(capacity=10, false_positive_rate=0)
        with self.assertRaises(ValueError):
            BloomFilter(capacity=10, false_positive_rate=1.5)

    def test_add_and_contains(self):
        bf = BloomFilter(capacity=100, false_positive_rate=0.01)
        self.assertTrue(bf.add("alice"))
        # adding the same item again reports it was already present
        self.assertFalse(bf.add("alice"))
        self.assertTrue(bf.contains("alice"))
        self.assertIn("alice", bf)

    def test_newly_added_count(self):
        bf = BloomFilter(capacity=100)
        bf.add_many(["a", "b", "c", "a"])
        self.assertEqual(len(bf), 3)

    def test_false_positive_rate(self):
        n = 2000
        bf = BloomFilter(capacity=n, false_positive_rate=0.01)
        for i in range(n):
            bf.add(f"item-{i}")
        false_positives = 0
        trials = 2000
        for i in range(trials):
            if bf.contains(f"absent-{i}"):
                false_positives += 1
        observed = false_positives / trials
        self.assertLess(observed, 0.05)

    def test_union(self):
        a = BloomFilter(capacity=100, seed=0)
        b = BloomFilter(capacity=100, seed=0)
        a.add_many(["x", "y"])
        b.add_many(["y", "z"])
        a.union(b)
        for item in ["x", "y", "z"]:
            self.assertTrue(a.contains(item))

    def test_union_incompatible(self):
        a = BloomFilter(capacity=100, seed=0)
        b = BloomFilter(capacity=100, seed=1)
        b.add("q")
        with self.assertRaises(IncompatibleFilterError):
            a.union(b)

    def test_serialization_roundtrip(self):
        bf = BloomFilter(capacity=200, false_positive_rate=0.02, seed=3)
        bf.add_many([f"k{i}" for i in range(50)])
        text = bf.to_json()
        restored = BloomFilter.from_json(text)
        self.assertEqual(bf.num_bits, restored.num_bits)
        self.assertEqual(bf.num_hashes, restored.num_hashes)
        self.assertEqual(bf.seed, restored.seed)
        for i in range(50):
            self.assertEqual(bf.contains(f"k{i}"), restored.contains(f"k{i}"))

    def test_approx_size(self):
        bf = BloomFilter(capacity=1000)
        bf.add_many([f"u{i}" for i in range(500)])
        size = bf.approx_size()
        self.assertGreater(size, 400)
        self.assertLess(size, 650)


if __name__ == "__main__":
    unittest.main()
