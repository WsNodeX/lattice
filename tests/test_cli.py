"""Tests for the command-line interface."""

from __future__ import annotations

import contextlib
import io
import unittest

from lattice import cli


class TestCli(unittest.TestCase):
    def test_bloom_subcommand(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli.main(["bloom", "--add", "alice,bob", "--check", "alice,zoe"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("contains('alice') = True", out)
        self.assertIn("contains('zoe') = False", out)

    def test_similarity_subcommand(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli.main(["similarity", "--set1", "a,b,c", "--set2", "a,b,d"])
        out = buf.getvalue()
        self.assertIn("Jaccard", out)

    def test_cardinality_subcommand(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli.main(["cardinality", "--items", "x,y,z,x", "--p", "8"])
        out = buf.getvalue()
        self.assertIn("distinct estimate", out)

    def test_demo_runs(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli.main(["demo"])
        self.assertEqual(rc, 0)
        self.assertIn("BloomFilter", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
