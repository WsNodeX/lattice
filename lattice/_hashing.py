"""Deterministic, dependency-free hashing primitives.

All hashes are computed with :mod:`hashlib.blake2b`, which is part of the
Python standard library and produces identical digests on every platform and
every run.  That determinism matters: it lets the test-suite assert exact
behaviour instead of "probably close enough", and it lets serialized filters
be reloaded and compared bit-for-bit.
"""

from __future__ import annotations

import hashlib
import json
from typing import Iterable, List

__all__ = [
    "item_to_bytes",
    "hashes",
    "hash64",
]

# A large odd constant used to decorrelate the per-index keys fed to blake2b.
_HASH_SPACING = 0x9E3779B1  # 2654435761


def item_to_bytes(item) -> bytes:
    """Normalise an arbitrary Python object into a stable byte string.

    The goal is *stability*: the same logical value always produces the same
    bytes, regardless of how it was constructed.  Strings, bytes, integers and
    JSON-serialisable containers are handled explicitly; everything else falls
    back to its ``str()`` representation.
    """
    if item is None:
        return b"\x00"
    if isinstance(item, (bytes, bytearray)):
        return bytes(item)
    if isinstance(item, str):
        return item.encode("utf-8")
    if isinstance(item, bool):
        # bool is a subclass of int; keep it distinct from 0/1.
        return b"b" + (b"1" if item else b"0")
    if isinstance(item, int):
        return b"i" + item.to_bytes((item.bit_length() + 8) // 8 or 1, "big", signed=True)
    if isinstance(item, (list, tuple, set, dict)):
        return b"j" + json.dumps(
            item, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    return b"s" + str(item).encode("utf-8")


def hashes(item, k: int, seed: int = 0) -> List[int]:
    """Return ``k`` independent 32-bit hashes of ``item``.

    Each hash is a BLAKE2b digest whose 64-bit *key* is the seed plus a unique
    offset per index.  Feeding a different key yields a statistically
    independent hash stream, which is exactly what Bloom filters, MinHash and
    similar structures need.
    """
    if k <= 0:
        raise ValueError("k must be a positive integer")
    data = item_to_bytes(item)
    out: List[int] = []
    for i in range(k):
        key = (seed + i * _HASH_SPACING) & 0xFFFFFFFFFFFFFFFF
        digest = hashlib.blake2b(data, digest_size=4, key=key.to_bytes(8, "big")).digest()
        out.append(int.from_bytes(digest, "big"))
    return out


def hash64(item, seed: int = 0) -> int:
    """Return a single stable 64-bit hash of ``item``.

    Used by HyperLogLog, which needs one wide hash that it can split into a
    bucket index plus the remaining bits for the rank computation.
    """
    data = item_to_bytes(item)
    key = seed & 0xFFFFFFFFFFFFFFFF
    digest = hashlib.blake2b(data, digest_size=8, key=key.to_bytes(8, "big")).digest()
    return int.from_bytes(digest, "big")


def bit_distribution(items: Iterable, k: int, modulus: int, seed: int = 0) -> float:
    """Helper used by tests: fraction of distinct (item, hash) positions.

    A healthy hash family maps distinct inputs to distinct positions; this
    returns how evenly the first hash of every item spreads across ``modulus``
    buckets (a quick sanity check, not a cryptographic property test).
    """
    seen = set()
    total = 0
    for item in items:
        pos = hashes(item, k, seed)[0] % modulus
        seen.add(pos)
        total += 1
    return (len(seen) / total) if total else 0.0
