"""Tests for MinHash and MinHashLSH."""

from __future__ import annotations

import unittest

from lattice import MinHash, MinHashLSH


class TestMinHash(unittest.TestCase):
    def test_identical_sets(self):
        a = MinHash(num_perm=64)
        a.update_batch(["x", "y", "z"])
        b = MinHash(num_perm=64)
        b.update_batch(["z", "y", "x"])
        self.assertAlmostEqual(a.jaccard(b), 1.0, places=6)

    def test_disjoint_sets(self):
        a = MinHash(num_perm=64)
        a.update_batch(["a", "b", "c"])
        b = MinHash(num_perm=64)
        b.update_batch(["d", "e", "f"])
        self.assertAlmostEqual(a.jaccard(b), 0.0, places=6)

    def test_known_jaccard(self):
        a = MinHash(num_perm=256)
        a.update_batch(f"e{i}" for i in range(100))
        b = MinHash(num_perm=256)
        b.update_batch(f"e{i}" for i in range(50))
        b.update_batch(f"f{i}" for i in range(50))
        # intersection 50, union 150 -> Jaccard 1/3
        self.assertLess(abs(a.jaccard(b) - 1 / 3), 0.12)

    def test_merge(self):
        a = MinHash(num_perm=64)
        a.update_batch(["p", "q"])
        b = MinHash(num_perm=64)
        b.update_batch(["q", "r"])
        merged = MinHash(num_perm=64)
        merged.merge(a).merge(b)
        ref = MinHash(num_perm=64)
        ref.update_batch(["p", "q", "r"])
        self.assertAlmostEqual(merged.jaccard(ref), 1.0, places=6)

    def test_serialization_roundtrip(self):
        a = MinHash(num_perm=64, seed=2)
        a.update_batch(["m", "n"])
        b = MinHash.from_json(a.to_json())
        self.assertEqual(a.hashvalues, b.hashvalues)
        self.assertEqual(a.jaccard(b), 1.0)

    def test_incompatible(self):
        a = MinHash(num_perm=64)
        b = MinHash(num_perm=32)
        with self.assertRaises(Exception):
            a.jaccard(b)


class TestMinHashLSH(unittest.TestCase):
    def test_optimal_bands_product(self):
        for threshold in (0.5, 0.8, 0.9):
            b, r = MinHashLSH._optimal_bands(128, threshold)
            self.assertEqual(b * r, 128)

    def test_query_identical(self):
        lsh = MinHashLSH(threshold=0.8, num_perm=128)
        m1 = MinHash(num_perm=128)
        m1.update_batch(["a", "b", "c"])
        m2 = MinHash(num_perm=128)
        m2.update_batch(["a", "b", "c"])
        lsh.insert("doc1", m1)
        lsh.insert("doc2", m2)
        self.assertEqual(lsh.query(m1), {"doc1", "doc2"})

    def test_query_disjoint(self):
        lsh = MinHashLSH(threshold=0.9, num_perm=128)
        m1 = MinHash(num_perm=128)
        m1.update_batch(f"x{i}" for i in range(50))
        m2 = MinHash(num_perm=128)
        m2.update_batch(f"y{i}" for i in range(50))
        lsh.insert("a", m1)
        lsh.insert("b", m2)
        # disjoint sets should not be returned as candidates at this threshold
        self.assertNotIn("b", lsh.query(m1))

    def test_duplicate_key(self):
        lsh = MinHashLSH(threshold=0.8, num_perm=64)
        m = MinHash(num_perm=64)
        m.update_batch(["k"])
        lsh.insert("a", m)
        with self.assertRaises(Exception):
            lsh.insert("a", m)

    def test_len(self):
        lsh = MinHashLSH(threshold=0.8, num_perm=64)
        m = MinHash(num_perm=64)
        m.update_batch(["k"])
        lsh.insert("a", m)
        self.assertEqual(len(lsh), 1)


if __name__ == "__main__":
    unittest.main()
