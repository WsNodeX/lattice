"""MinHash and Locality-Sensitive Hashing for near-duplicate detection.

MinHash compresses a set into a fixed-length signature such that the fraction
of equal positions between two signatures estimates their Jaccard similarity.
LSH (Locality-Sensitive Hashing) bands those signatures so that similar sets
land in the same bucket with high probability -- turning an O(n**2) all-pairs
comparison into an O(n) lookup, which is how systems like near-duplicate
web-page detection and plagiarism checkers scale.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from ._hashing import hashes
from .errors import LatticeError

__all__ = ["MinHash", "MinHashLSH"]

_MAX_HASH = (1 << 32) - 1


class MinHash:
    """A MinHash signature of a set.

    Parameters
    ----------
    num_perm:
        Number of hash permutations (signature length).  Larger values reduce
        estimation variance; 128-256 is typical.
    seed:
        Hash seed; compare only signatures built with the same seed and
        ``num_perm``.
    """

    def __init__(self, num_perm: int = 128, seed: int = 1):
        if num_perm <= 0:
            raise ValueError("num_perm must be a positive integer")
        self.num_perm = num_perm
        self.seed = seed
        self.hashvalues: List[int] = [_MAX_HASH] * num_perm

    def update(self, item) -> None:
        """Incorporate a single element into the signature."""
        row = hashes(item, self.num_perm, self.seed)
        vals = self.hashvalues
        for i in range(self.num_perm):
            v = row[i]
            if v < vals[i]:
                vals[i] = v

    def update_batch(self, items: Iterable) -> None:
        for item in items:
            self.update(item)

    # alias kept for ergonomics
    def add(self, item) -> None:
        self.update(item)

    def jaccard(self, other: "MinHash") -> float:
        """Estimate Jaccard similarity with ``other`` from the signatures."""
        if not isinstance(other, MinHash):
            raise LatticeError("can only compare with another MinHash")
        if self.num_perm != other.num_perm or self.seed != other.seed:
            raise LatticeError("signatures differ in num_perm or seed")
        equal = sum(1 for a, b in zip(self.hashvalues, other.hashvalues) if a == b)
        return equal / self.num_perm

    similarity = jaccard

    def merge(self, other: "MinHash") -> "MinHash":
        if self.num_perm != other.num_perm or self.seed != other.seed:
            raise LatticeError("signatures differ in num_perm or seed")
        for i in range(self.num_perm):
            if other.hashvalues[i] < self.hashvalues[i]:
                self.hashvalues[i] = other.hashvalues[i]
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "minhash",
            "num_perm": self.num_perm,
            "seed": self.seed,
            "hashvalues": self.hashvalues,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MinHash":
        if data.get("type") != "minhash":
            raise LatticeError("not a minhash payload")
        obj = cls(data["num_perm"], data["seed"])
        obj.hashvalues = list(data["hashvalues"])
        return obj

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, text: str) -> "MinHash":
        return cls.from_dict(json.loads(text))


class MinHashLSH:
    """Band the MinHash signatures of many sets for fast similarity queries.

    Parameters
    ----------
    threshold:
        Target Jaccard similarity above which two sets should be returned as
        candidates.  The band/row split is chosen to make the probability of
        becoming a candidate cross ``threshold``.
    num_perm:
        Signature length, must match the inserted MinHash objects.
    b, r:
        Explicit band count and rows-per-band.  When omitted they are chosen
        from ``threshold`` and ``num_perm`` (``b * r == num_perm``).
    """

    def __init__(
        self,
        threshold: float = 0.8,
        num_perm: int = 128,
        b: Optional[int] = None,
        r: Optional[int] = None,
    ):
        if not 0.0 < threshold < 1.0:
            raise ValueError("threshold must be between 0 and 1 (exclusive)")
        if b is None or r is None:
            b, r = self._optimal_bands(num_perm, threshold)
        if b * r != num_perm:
            raise ValueError("b * r must equal num_perm")
        self.threshold = threshold
        self.num_perm = num_perm
        self.b = b
        self.r = r
        self._buckets: Dict[Tuple[int, int], List[str]] = {}
        self._entries: Dict[str, MinHash] = {}

    @staticmethod
    def _optimal_bands(num_perm: int, threshold: float) -> Tuple[int, int]:
        best: Optional[Tuple[float, int, int]] = None
        for b in range(1, num_perm + 1):
            if num_perm % b != 0:
                continue
            r = num_perm // b
            # probability two sets with similarity s become candidates
            prob = (1.0 - (1.0 - threshold ** r)) ** b
            err = abs(prob - threshold)
            if best is None or err < best[0]:
                best = (err, b, r)
        assert best is not None
        return best[1], best[2]

    def _band_hash(self, sig: MinHash, band: int) -> int:
        start = band * self.r
        end = start + self.r
        return hash(tuple(sig.hashvalues[start:end]))

    def insert(self, key: str, minhash: MinHash) -> None:
        if key in self._entries:
            raise LatticeError(f"key {key!r} already inserted")
        if minhash.num_perm != self.num_perm:
            raise LatticeError("minhash num_perm does not match this index")
        self._entries[key] = minhash
        for band in range(self.b):
            h = self._band_hash(minhash, band)
            self._buckets.setdefault((band, h), []).append(key)

    def query(self, minhash: MinHash) -> Set[str]:
        """Return candidate keys sharing at least one band with ``minhash``."""
        if minhash.num_perm != self.num_perm:
            raise LatticeError("minhash num_perm does not match this index")
        candidates: Set[str] = set()
        for band in range(self.b):
            h = self._band_hash(minhash, band)
            for key in self._buckets.get((band, h), ()):
                candidates.add(key)
        return candidates

    def __contains__(self, key: str) -> bool:
        return key in self._entries

    def __len__(self) -> int:
        return len(self._entries)
