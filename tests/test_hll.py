"""Tests for HyperLogLog cardinality estimation."""

from __future__ import annotations

import unittest

from lattice import HyperLogLog


class TestHyperLogLog(unittest.TestCase):
    def test_invalid_p(self):
        with self.assertRaises(ValueError):
            HyperLogLog(p=3)
        with self.assertRaises(ValueError):
            HyperLogLog(p=20)

    def test_empty_is_zero(self):
        hll = HyperLogLog(p=10)
        self.assertEqual(hll.count(), 0)
        self.assertEqual(len(hll), 0)

    def test_small_exactish(self):
        hll = HyperLogLog(p=12)
        hll.add_many([f"u{i}" for i in range(100)])
        est = hll.count()
        self.assertLess(abs(est - 100) / 100, 0.3)

    def test_accuracy(self):
        hll = HyperLogLog(p=14)
        for n in (1000, 5000, 20000):
            h = HyperLogLog(p=14)
            h.add_many(f"id-{i}" for i in range(n))
            rel = abs(h.count() - n) / n
            self.assertLess(rel, 0.1, msg=f"n={n} rel err={rel:.3f}")

    def test_merge(self):
        a = HyperLogLog(p=12, seed=0)
        b = HyperLogLog(p=12, seed=0)
        a.add_many(f"x{i}" for i in range(5000))
        b.add_many(f"y{i}" for i in range(5000))
        a.merge(b)
        rel = abs(a.count() - 10000) / 10000
        self.assertLess(rel, 0.1)

    def test_serialization_roundtrip(self):
        hll = HyperLogLog(p=10, seed=4)
        hll.add_many([f"z{i}" for i in range(200)])
        restored = HyperLogLog.from_json(hll.to_json())
        self.assertEqual(hll.count(), restored.count())
        self.assertEqual(list(hll.registers), list(restored.registers))


if __name__ == "__main__":
    unittest.main()
