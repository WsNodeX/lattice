"""Count-Min Sketch: approximate frequency counting in sub-linear space.

A Count-Min Sketch answers *"how many times have I seen X?"* using a small
two-dimensional counter array.  It never underestimates and overestimates only
by colliding with other heavy items.  That makes it ideal for top-k, trending
and anomaly detection on streams that are far too large to keep in memory.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List

from ._hashing import hashes
from .errors import IncompatibleFilterError

__all__ = ["CountMinSketch"]


class CountMinSketch:
    """A Count-Min Sketch.

    Parameters
    ----------
    width:
        Number of counters per row.  A wider table lowers collision error.
        A common choice is ``width = ceil(2 / error)``.
    depth:
        Number of independent hash rows.  More rows reduces the chance that all
        of them collide.  A common choice is ``depth = ceil(ln(1 / delta))``.
    seed:
        Hash seed; merge only sketches that share it.
    """

    def __init__(self, width: int = 1000, depth: int = 5, seed: int = 0):
        if width <= 0 or depth <= 0:
            raise ValueError("width and depth must be positive integers")
        self.width = width
        self.depth = depth
        self.seed = seed
        self.table: List[List[int]] = [[0] * width for _ in range(depth)]

    def _indices(self, item) -> List[int]:
        row_hashes = hashes(item, self.depth, self.seed)
        return [row_hashes[i] % self.width for i in range(self.depth)]

    def add(self, item, count: int = 1) -> None:
        """Increment the frequency estimate of ``item`` by ``count``."""
        if count < 0:
            raise ValueError("count must be non-negative")
        idx = self._indices(item)
        for i in range(self.depth):
            self.table[i][idx[i]] += count

    def estimate(self, item) -> int:
        """Return the (over-)estimated frequency of ``item``.

        The estimate is the minimum across all rows, which is the standard
        Count-Min query and guarantees no under-counting.
        """
        idx = self._indices(item)
        return min(self.table[i][idx[i]] for i in range(self.depth))

    def total(self) -> int:
        """Sum of every counter in the first row (an upper bound on events)."""
        return sum(self.table[0])

    def __getitem__(self, item) -> int:
        return self.estimate(item)

    def merge(self, other: "CountMinSketch") -> "CountMinSketch":
        """In-place additive merge with ``other``.

        When two sketches summarise disjoint sub-streams, adding their counter
        tables yields the correct combined frequency estimate (the standard
        way to combine Count-Min sketches across machines).
        """
        self._require_compatible(other)
        for i in range(self.depth):
            row = self.table[i]
            orow = other.table[i]
            for j in range(self.width):
                row[j] += orow[j]
        return self

    def inner_product(self, other: "CountMinSketch") -> int:
        """Approximate ``sum_x freq(x) * other_freq(x)`` via min-of-counters.

        Useful as a cheap similarity proxy between two streams.
        """
        self._require_compatible(other)
        total = 0
        for i in range(self.depth):
            row = self.table[i]
            orow = other.table[i]
            for j in range(self.width):
                total += min(row[j], orow[j])
        return total

    def _require_compatible(self, other: "CountMinSketch") -> None:
        if not isinstance(other, CountMinSketch):
            raise IncompatibleFilterError("can only combine with another CountMinSketch")
        if self.width != other.width or self.depth != other.depth or self.seed != other.seed:
            raise IncompatibleFilterError("sketches differ in width, depth or seed")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "cms",
            "width": self.width,
            "depth": self.depth,
            "seed": self.seed,
            "table": self.table,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CountMinSketch":
        if data.get("type") != "cms":
            raise ValueError("not a count-min sketch payload")
        obj = cls(data["width"], data["depth"], data["seed"])
        obj.table = [list(row) for row in data["table"]]
        return obj

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, text: str) -> "CountMinSketch":
        return cls.from_dict(json.loads(text))
