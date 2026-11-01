"""Tests for CountingBloomFilter."""

from __future__ import annotations

import unittest

from lattice import CountingBloomFilter


class TestCountingBloomFilter(unittest.TestCase):
    def test_add_and_contains(self):
        cbf = CountingBloomFilter(capacity=100)
        cbf.add("a")
        self.assertTrue(cbf.contains("a"))

    def test_remove(self):
        cbf = CountingBloomFilter(capacity=100)
        cbf.add("a")
        cbf.add("a")
        self.assertTrue(cbf.remove("a"))
        self.assertTrue(cbf.contains("a"))
        self.assertTrue(cbf.remove("a"))
        self.assertFalse(cbf.contains("a"))

    def test_remove_absent(self):
        cbf = CountingBloomFilter(capacity=100)
        self.assertFalse(cbf.remove("nope"))

    def test_remove_once(self):
        cbf = CountingBloomFilter(capacity=50)
        cbf.add("x")
        self.assertTrue(cbf.remove("x"))
        self.assertFalse(cbf.contains("x"))
        # removing an already-absent item reports False
        self.assertFalse(cbf.remove("x"))

    def test_serialization_roundtrip(self):
        cbf = CountingBloomFilter(capacity=120, seed=5)
        cbf.add_many(["a", "b", "c", "a"])
        restored = CountingBloomFilter.from_json(cbf.to_json())
        self.assertEqual(cbf.contains("a"), restored.contains("a"))
        self.assertEqual(cbf.contains("z"), restored.contains("z"))
        self.assertEqual(cbf._counts, restored._counts)

    def test_len_counts_new(self):
        cbf = CountingBloomFilter(capacity=50)
        cbf.add("a")
        cbf.add("a")
        cbf.add("b")
        self.assertEqual(len(cbf), 2)


if __name__ == "__main__":
    unittest.main()
