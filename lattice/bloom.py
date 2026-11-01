"""Space-efficient probabilistic set membership.

A Bloom filter answers the question *"have I seen this item?"* using a fraction
of the memory a hash-set would need, at the cost of a small, bounded false
positive rate.  A :class:`CountingBloomFilter` adds deletion support by storing
small counters instead of single bits.
"""

from __future__ import annotations

import base64
import json
import math
from typing import Any, Dict, Iterable, List

from ._hashing import hashes
from .errors import IncompatibleFilterError, LatticeError

__all__ = ["BloomFilter", "CountingBloomFilter"]


def _optimal_params(capacity: int, false_positive_rate: float):
    """Return ``(num_bits, num_hashes)`` for a target capacity and FPR."""
    n = capacity
    p = false_positive_rate
    num_bits = math.ceil(-(n * math.log(p)) / (math.log(2) ** 2))
    num_hashes = math.ceil((num_bits / n) * math.log(2))
    return num_bits, num_hashes


class BloomFilter:
    """A classic Bloom filter.

    Parameters
    ----------
    capacity:
        Expected number of items.  Sizing for this many items keeps the false
        positive rate near ``false_positive_rate``.
    false_positive_rate:
        Target probability (strictly between 0 and 1) of a false positive.
    seed:
        Hash seed; combine only filters that share the same seed.
    """

    def __init__(self, capacity: int, false_positive_rate: float = 0.01, seed: int = 0):
        if capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        if not 0.0 < false_positive_rate < 1.0:
            raise ValueError("false_positive_rate must be between 0 and 1 (exclusive)")

        self.capacity = capacity
        self.false_positive_rate = false_positive_rate
        self.seed = seed
        self.num_bits, self.num_hashes = _optimal_params(capacity, false_positive_rate)
        self._bytes = bytearray((self.num_bits + 7) // 8)
        self._count = 0

    # ------------------------------------------------------------------ bits
    def _get(self, pos: int) -> int:
        return (self._bytes[pos >> 3] >> (pos & 7)) & 1

    def _set(self, pos: int, val: int) -> None:
        if val:
            self._bytes[pos >> 3] |= 1 << (pos & 7)
        else:
            self._bytes[pos >> 3] &= ~(1 << (pos & 7))

    def _positions(self, item) -> List[int]:
        return [h % self.num_bits for h in hashes(item, self.num_hashes, self.seed)]

    # ----------------------------------------------------------------- membership
    def add(self, item) -> bool:
        """Insert ``item``.  Returns ``True`` if it was absent before."""
        positions = self._positions(item)
        was_present = all(self._get(p) for p in positions)
        for p in positions:
            self._set(p, 1)
        if not was_present:
            self._count += 1
        return not was_present

    def add_many(self, items: Iterable) -> int:
        """Insert several items; return how many were newly added."""
        added = 0
        for item in items:
            if self.add(item):
                added += 1
        return added

    def contains(self, item) -> bool:
        """Return ``True`` if ``item`` was (probably) inserted."""
        return all(self._get(p) for p in self._positions(item))

    def __contains__(self, item) -> bool:
        return self.contains(item)

    def __len__(self) -> int:
        return self._count

    # ------------------------------------------------------------------ utils
    def approx_size(self) -> int:
        """Estimate how many distinct items have been inserted.

        Uses the standard formula derived from the expected number of set bits.
        """
        ones = sum(self._get(i) for i in range(self.num_bits))
        if ones == 0:
            return 0
        if ones == self.num_bits:
            return self._count
        n = -(self.num_bits / self.num_hashes) * math.log(1.0 - ones / self.num_bits)
        return int(round(n))

    def union(self, other: "BloomFilter") -> "BloomFilter":
        """In-place bitwise OR with ``other`` (must be identical config)."""
        self._require_compatible(other)
        for i in range(len(self._bytes)):
            self._bytes[i] |= other._bytes[i]
        self._count = max(self._count, other._count)
        return self

    def _require_compatible(self, other: "BloomFilter") -> None:
        if not isinstance(other, BloomFilter):
            raise IncompatibleFilterError("can only combine with another BloomFilter")
        if (
            self.num_bits != other.num_bits
            or self.num_hashes != other.num_hashes
            or self.seed != other.seed
        ):
            raise IncompatibleFilterError(
                "filters differ in size, hash count or seed"
            )

    # -------------------------------------------------------------- (de)serialise
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "bloom",
            "capacity": self.capacity,
            "false_positive_rate": self.false_positive_rate,
            "seed": self.seed,
            "num_bits": self.num_bits,
            "num_hashes": self.num_hashes,
            "count": self._count,
            "bits": base64.b64encode(bytes(self._bytes)).decode("ascii"),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BloomFilter":
        if data.get("type") != "bloom":
            raise LatticeError("not a bloom filter payload")
        obj = cls(data["capacity"], data["false_positive_rate"], data["seed"])
        raw = base64.b64decode(data["bits"])
        obj._bytes = bytearray(raw)
        obj._count = int(data.get("count", 0))
        return obj

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, text: str) -> "BloomFilter":
        return cls.from_dict(json.loads(text))


class CountingBloomFilter:
    """A Bloom filter that supports deletion via small per-cell counters.

    Identical to :class:`BloomFilter` for membership tests, but every hash
    position stores an 8-bit counter (0-255) instead of a single bit, so items
    can be removed without rebuilding the whole structure.
    """

    def __init__(self, capacity: int, false_positive_rate: float = 0.01, seed: int = 0):
        if capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        if not 0.0 < false_positive_rate < 1.0:
            raise ValueError("false_positive_rate must be between 0 and 1 (exclusive)")

        self.capacity = capacity
        self.false_positive_rate = false_positive_rate
        self.seed = seed
        self.num_bits, self.num_hashes = _optimal_params(capacity, false_positive_rate)
        self._counts = [0] * self.num_bits
        self._count = 0

    def _positions(self, item) -> List[int]:
        return [h % self.num_bits for h in hashes(item, self.num_hashes, self.seed)]

    def add(self, item) -> bool:
        positions = self._positions(item)
        was_present = all(self._counts[p] > 0 for p in positions)
        for p in positions:
            if self._counts[p] < 255:
                self._counts[p] += 1
        if not was_present:
            self._count += 1
        return not was_present

    def add_many(self, items: Iterable) -> int:
        """Insert several items; return how many were newly added."""
        added = 0
        for item in items:
            if self.add(item):
                added += 1
        return added

    def remove(self, item) -> bool:
        """Decrement counters for ``item``.  Returns ``True`` if it was present."""
        positions = self._positions(item)
        if not all(self._counts[p] > 0 for p in positions):
            return False
        for p in positions:
            if self._counts[p] > 0:
                self._counts[p] -= 1
        self._count = max(0, self._count - 1)
        return True

    def contains(self, item) -> bool:
        return all(self._counts[p] > 0 for p in self._positions(item))

    def __contains__(self, item) -> bool:
        return self.contains(item)

    def __len__(self) -> int:
        return self._count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "counting_bloom",
            "capacity": self.capacity,
            "false_positive_rate": self.false_positive_rate,
            "seed": self.seed,
            "num_bits": self.num_bits,
            "num_hashes": self.num_hashes,
            "count": self._count,
            "counts": base64.b64encode(bytes(self._counts)).decode("ascii"),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CountingBloomFilter":
        if data.get("type") != "counting_bloom":
            raise LatticeError("not a counting bloom filter payload")
        obj = cls(data["capacity"], data["false_positive_rate"], data["seed"])
        obj._counts = list(base64.b64decode(data["counts"]))
        obj._count = int(data.get("count", 0))
        return obj

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, text: str) -> "CountingBloomFilter":
        return cls.from_dict(json.loads(text))
