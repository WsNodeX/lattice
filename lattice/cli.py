"""Command-line interface for the :mod:`lattice` package.

Usage examples
--------------
    python -m lattice.cli demo
    python -m lattice.cli bloom --add alice bob carol --check bob zoe
    python -m lattice.cli cardinality --items a b c d e f
    python -m lattice.cli similarity --set1 a,b,c --set2 a,b,d
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from .bloom import BloomFilter
from .cms import CountMinSketch
from .hll import HyperLogLog
from .minhash import MinHash


def _split(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [v for v in value.split(",") if v != ""]


def cmd_bloom(args: argparse.Namespace) -> int:
    items = _split(args.add)
    bf = BloomFilter(capacity=max(16, len(items) * 4), false_positive_rate=args.fpr)
    added = bf.add_many(items)
    print(f"BloomFilter: capacity={bf.capacity} hashes={bf.num_hashes} bits={bf.num_bits}")
    print(f"inserted {added} new item(s); approx_size={bf.approx_size()}")
    for probe in _split(args.check):
        print(f"  contains({probe!r}) = {bf.contains(probe)}")
    return 0


def cmd_cardinality(args: argparse.Namespace) -> int:
    items = _split(args.items)
    if not items and not sys.stdin.isatty():
        items = [line.strip() for line in sys.stdin if line.strip()]
    hll = HyperLogLog(p=args.p)
    hll.add_many(items)
    print(f"HyperLogLog(p={args.p}): distinct estimate = {hll.count():.0f}")
    print(f"actual inserted        = {len(set(items))}")
    return 0


def cmd_similarity(args: argparse.Namespace) -> int:
    a = MinHash(num_perm=args.num_perm)
    a.update_batch(_split(args.set1))
    b = MinHash(num_perm=args.num_perm)
    b.update_batch(_split(args.set2))
    print(f"MinHash(num_perm={args.num_perm}): estimated Jaccard = {a.jaccard(b):.3f}")
    return 0


def cmd_demo(_args: argparse.Namespace) -> int:
    print("=" * 60)
    print("lattice -- probabilistic data structures in pure Python")
    print("=" * 60)

    print("\n[1] BloomFilter -- set membership")
    bf = BloomFilter(capacity=1000, false_positive_rate=0.01)
    for i in range(500):
        bf.add(f"user-{i}")
    print(f"    inserted 500 users; approx_size = {bf.approx_size()}")
    print(f"    contains('user-42')  = {bf.contains('user-42')}  (true)")
    print(f"    contains('ghost')    = {bf.contains('ghost')}  (probably false)")

    print("\n[2] CountMinSketch -- frequency counting")
    cms = CountMinSketch(width=200, depth=5)
    for _ in range(100):
        cms.add("hot-key")
    cms.add("rare-key", 1)
    print(f"    estimate('hot-key')  = {cms.estimate('hot-key')}  (true 100)")
    print(f"    estimate('rare-key') = {cms.estimate('rare-key')}  (true 1)")

    print("\n[3] HyperLogLog -- cardinality estimation")
    hll = HyperLogLog(p=12)
    hll.add_many(f"ip-{i}" for i in range(10000))
    print(f"    distinct estimate = {hll.count():.0f}  (true 10000)")

    print("\n[4] MinHash -- Jaccard similarity")
    a = MinHash(num_perm=128)
    a.update_batch([f"w-{i}" for i in range(100)])
    b = MinHash(num_perm=128)
    b.update_batch([f"w-{i}" for i in range(50, 150)])
    # intersection 50, union 150 -> Jaccard 1/3
    print(f"    estimated Jaccard = {a.jaccard(b):.3f}  (true ~0.333)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lattice",
        description="Zero-dependency probabilistic data structures.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_bloom = sub.add_parser("bloom", help="test set membership")
    p_bloom.add_argument("--add", help="comma-separated items to insert")
    p_bloom.add_argument("--check", help="comma-separated items to test")
    p_bloom.add_argument("--fpr", type=float, default=0.01)
    p_bloom.set_defaults(func=cmd_bloom)

    p_card = sub.add_parser("cardinality", help="estimate distinct count")
    p_card.add_argument("--items", help="comma-separated items")
    p_card.add_argument("--p", type=int, default=14, help="bucket bits (4-18)")
    p_card.set_defaults(func=cmd_cardinality)

    p_sim = sub.add_parser("similarity", help="estimate Jaccard similarity")
    p_sim.add_argument("--set1", help="comma-separated items")
    p_sim.add_argument("--set2", help="comma-separated items")
    p_sim.add_argument("--num-perm", type=int, default=128)
    p_sim.set_defaults(func=cmd_similarity)

    p_demo = sub.add_parser("demo", help="run a self-contained tour")
    p_demo.set_defaults(func=cmd_demo)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
