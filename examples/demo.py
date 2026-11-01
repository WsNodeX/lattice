"""End-to-end tour of every structure in ``lattice``.

Run with:: python examples/demo.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lattice import BloomFilter, CountMinSketch, HyperLogLog, MinHash


def main() -> None:
    print("lattice demo\n" + "=" * 40)

    # 1. Bloom filter
    bf = BloomFilter(capacity=1000, false_positive_rate=0.01)
    for i in range(500):
        bf.add(f"user-{i}")
    print("Bloom: inserted 500; approx_size =", bf.approx_size())
    print("  contains user-42 ->", bf.contains("user-42"))
    print("  contains nobody  ->", bf.contains("nobody"))

    # 2. Count-Min sketch
    cms = CountMinSketch(width=256, depth=5)
    for _ in range(1000):
        cms.add("trending")
    cms.add("once")
    print("\nCountMin: trending estimate =", cms.estimate("trending"), "(true 1000)")
    print("  once estimate =", cms.estimate("once"), "(true 1)")

    # 3. HyperLogLog
    hll = HyperLogLog(p=14)
    hll.add_many(f"visitor-{i}" for i in range(50000))
    print("\nHyperLogLog: distinct estimate =", round(hll.count()), "(true 50000)")

    # 4. MinHash
    a = MinHash(num_perm=128)
    a.update_batch(f"token-{i}" for i in range(100))
    b = MinHash(num_perm=128)
    b.update_batch(f"token-{i}" for i in range(50, 150))
    print("\nMinHash: Jaccard estimate =", round(a.jaccard(b), 3), "(true 0.333)")


if __name__ == "__main__":
    main()
