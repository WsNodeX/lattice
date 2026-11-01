"""Near-duplicate document detection with MinHash + LSH.

This mirrors the technique large crawlers use to spot duplicated or lightly
rewritten pages: shingle each document into a set of n-grams, build a MinHash
signature per document, and band those signatures so near-duplicates collide
into the same bucket with high probability.

Run with:: python examples/near_duplicate.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lattice import MinHash, MinHashLSH


def shingles(text: str, k: int = 3) -> set:
    words = text.lower().split()
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}


DOCUMENTS = {
    "doc_a": "the quick brown fox jumps over the lazy dog near the river bank",
    "doc_b": "the quick brown fox jumps over the lazy dog near the river bank",  # exact dup
    "doc_c": "a quick brown fox jumps over a lazy dog that rests near the river",  # near dup
    "doc_d": "machine learning models require large datasets and careful tuning",  # unrelated
}


def main() -> None:
    num_perm = 128
    lsh = MinHashLSH(threshold=0.6, num_perm=num_perm)

    signatures = {}
    for key, text in DOCUMENTS.items():
        mh = MinHash(num_perm=num_perm)
        mh.update_batch(shingles(text))
        signatures[key] = mh
        lsh.insert(key, mh)

    query_key = "doc_a"
    candidates = lsh.query(signatures[query_key])
    print(f"Query: {query_key}")
    print("Candidate near-duplicates (same LSH bucket):", sorted(candidates))
    for other in sorted(candidates):
        if other == query_key:
            continue
        j = signatures[query_key].jaccard(signatures[other])
        print(f"  {query_key} <-> {other}: Jaccard = {j:.3f}")


if __name__ == "__main__":
    main()
