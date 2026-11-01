"""HyperLogLog: estimate the number of distinct items in a stream.

HyperLogLog solves the *cardinality estimation* problem: how many unique
elements have appeared in a massive, possibly infinite stream, using only a few
kilobytes of memory.  It hashes every item to 64 bits, uses the top ``p`` bits
as a bucket and records the longest run of leading zeros seen in the remainder.
A clever bias-corrected average over buckets yields an estimate accurate to
roughly ``1.04 / sqrt(2**p)``.
"""

from __future__ import annotations

import json
import math
from typing import Any, Dict, Iterable

from ._hashing import hash64
from .errors import IncompatibleFilterError

__all__ = ["HyperLogLog"]


def _alpha(m: int) -> float:
    """Small-range bias correction constant for ``m`` registers."""
    if m == 16:
        return 0.673
    if m == 32:
        return 0.697
    if m == 64:
        return 0.709
    return 0.7213 / (1.0 + 1.079 / m)


class HyperLogLog:
    """A HyperLogLog cardinality estimator.

    Parameters
    ----------
    p:
        Number of bucket bits.  The structure keeps ``2**p`` registers, so
        memory use is ``2**p`` bytes.  Accuracy scales as ``1.04/sqrt(2**p)``.
        Must be between 4 and 18 inclusive.
    seed:
        Hash seed; merge only estimators that share it and ``p``.
    """

    def __init__(self, p: int = 14, seed: int = 0):
        if not 4 <= p <= 18:
            raise ValueError("p must be between 4 and 18 inclusive")
        self.p = p
        self.m = 1 << p
        self.seed = seed
        self.registers = bytearray(self.m)

    def add(self, item) -> None:
        """Incorporate ``item`` into the cardinality estimate."""
        x = hash64(item, self.seed)
        idx = x >> (64 - self.p)
        w = x & ((1 << (64 - self.p)) - 1)
        # rho = number of leading zeros in w (+1); w occupies (64-p) bits.
        rho = (64 - self.p) - w.bit_length() + 1
        if rho > self.registers[idx]:
            self.registers[idx] = rho

    def add_many(self, items: Iterable) -> None:
        for item in items:
            self.add(item)

    def count(self) -> float:
        """Return the estimated number of distinct items seen so far."""
        m = self.m
        est = _alpha(m) * m * m / sum(2.0 ** (-r) for r in self.registers)

        # Small-range correction: if there are empty registers, linear counting
        # is far more accurate than the harmonic mean.
        zeros = self.registers.count(0)
        if zeros > 0:
            lc = m * math.log(m / zeros)
            if lc <= 2.5 * m:
                est = lc

        # Large-range correction: guard against 32-bit overflow effects.
        if est > (1 << 32) / 30:
            est = -(1 << 32) * math.log(1.0 - est / (1 << 32))

        return est

    def __len__(self) -> int:
        return int(round(self.count()))

    def merge(self, other: "HyperLogLog") -> "HyperLogLog":
        """In-place register-wise maximum merge with ``other``."""
        if not isinstance(other, HyperLogLog):
            raise IncompatibleFilterError("can only combine with another HyperLogLog")
        if self.p != other.p or self.seed != other.seed:
            raise IncompatibleFilterError("estimators differ in p or seed")
        for i in range(self.m):
            if other.registers[i] > self.registers[i]:
                self.registers[i] = other.registers[i]
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "hll",
            "p": self.p,
            "seed": self.seed,
            "registers": list(self.registers),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HyperLogLog":
        if data.get("type") != "hll":
            raise ValueError("not a hyperloglog payload")
        obj = cls(data["p"], data["seed"])
        obj.registers = bytearray(data["registers"])
        return obj

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, text: str) -> "HyperLogLog":
        return cls.from_dict(json.loads(text))
