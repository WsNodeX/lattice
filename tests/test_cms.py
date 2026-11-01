"""Tests for CountMinSketch."""

from __future__ import annotations

import unittest

from lattice import CountMinSketch


class TestCountMinSketch(unittest.TestCase):
    def test_unseen_is_zero(self):
        cms = CountMinSketch(width=64, depth=4)
        self.assertEqual(cms.estimate("ghost"), 0)
        self.assertEqual(cms["ghost"], 0)

    def test_single_item_exact(self):
        cms = CountMinSketch(width=100, depth=5)
        cms.add("only", 7)
        # a single item maps to one column per row -> estimate is exact
        self.assertEqual(cms.estimate("only"), 7)

    def test_never_underestimates(self):
        cms = CountMinSketch(width=256, depth=6)
        items = {f"k{i}": (i % 5) + 1 for i in range(200)}
        for k, c in items.items():
            cms.add(k, c)
        for k, c in items.items():
            self.assertGreaterEqual(cms.estimate(k), c)

    def test_merge(self):
        a = CountMinSketch(width=128, depth=4, seed=0)
        b = CountMinSketch(width=128, depth=4, seed=0)
        a.add("x", 10)
        b.add("x", 5)
        a.merge(b)
        self.assertGreaterEqual(a.estimate("x"), 15)

    def test_inner_product(self):
        a = CountMinSketch(width=64, depth=3, seed=0)
        b = CountMinSketch(width=64, depth=3, seed=0)
        a.add("x", 3)
        b.add("x", 2)
        # min(3,2)=2 for the shared column
        self.assertGreaterEqual(a.inner_product(b), 2)

    def test_serialization_roundtrip(self):
        cms = CountMinSketch(width=80, depth=4, seed=2)
        cms.add("alpha", 5)
        cms.add("beta", 9)
        restored = CountMinSketch.from_json(cms.to_json())
        self.assertEqual(cms.estimate("alpha"), restored.estimate("alpha"))
        self.assertEqual(cms.estimate("beta"), restored.estimate("beta"))

    def test_invalid_params(self):
        with self.assertRaises(ValueError):
            CountMinSketch(width=0)


if __name__ == "__main__":
    unittest.main()
