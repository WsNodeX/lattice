"""Tests for the hashing primitives."""

from __future__ import annotations

import unittest

from lattice._hashing import bit_distribution, hash64, hashes, item_to_bytes


class TestItemToBytes(unittest.TestCase):
    def test_str(self):
        self.assertEqual(item_to_bytes("hi"), b"hi")

    def test_bytes_passthrough(self):
        self.assertEqual(item_to_bytes(b"hi"), b"hi")

    def test_int_signed(self):
        self.assertEqual(item_to_bytes(0), b"i\x00")
        self.assertNotEqual(item_to_bytes(1), item_to_bytes(-1))

    def test_bool_distinct_from_int(self):
        self.assertNotEqual(item_to_bytes(True), item_to_bytes(1))

    def test_container_sorted(self):
        # dicts must serialise deterministically regardless of insertion order
        self.assertEqual(item_to_bytes({"b": 1, "a": 2}), item_to_bytes({"a": 2, "b": 1}))


class TestHashes(unittest.TestCase):
    def test_length(self):
        self.assertEqual(len(hashes("x", 7)), 7)

    def test_deterministic(self):
        self.assertEqual(hashes("hello", 5, 0), hashes("hello", 5, 0))

    def test_seed_changes_output(self):
        self.assertNotEqual(hashes("hello", 5, 0), hashes("hello", 5, 1))

    def test_distribution(self):
        items = [f"v{i}" for i in range(2000)]
        # with a 32-bit bucket space, 2000 items essentially never collide
        frac = bit_distribution(items, 1, 1 << 32, 0)
        self.assertGreater(frac, 0.95)


class TestHash64(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(hash64("abc"), hash64("abc"))

    def test_range(self):
        self.assertTrue(0 <= hash64("abc") < (1 << 64))


if __name__ == "__main__":
    unittest.main()
