"""lattice -- zero-dependency probabilistic data structures in pure Python.

This package ships four classic, memory-frugal structures that trade a small,
bounded error for orders-of-magnitude less space than exact data structures:

* :class:`~lattice.bloom.BloomFilter` / :class:`~lattice.bloom.CountingBloomFilter`
  -- probabilistic set membership (and deletion).
* :class:`~lattice.cms.CountMinSketch` -- approximate frequency counting.
* :class:`~lattice.hll.HyperLogLog` -- distinct-count (cardinality) estimation.
* :class:`~lattice.minhash.MinHash` / :class:`~lattice.minhash.MinHashLSH`
  -- Jaccard similarity estimation and near-duplicate indexing.

Everything is implemented on top of the standard library only; there are no
third-party dependencies and nothing to compile.
"""

from __future__ import annotations

from .bloom import BloomFilter, CountingBloomFilter
from .cms import CountMinSketch
from .errors import IncompatibleFilterError, LatticeError
from .hll import HyperLogLog
from .minhash import MinHash, MinHashLSH

__version__ = "0.1.0"

__all__ = [
    "BloomFilter",
    "CountingBloomFilter",
    "CountMinSketch",
    "HyperLogLog",
    "MinHash",
    "MinHashLSH",
    "LatticeError",
    "IncompatibleFilterError",
    "__version__",
]
