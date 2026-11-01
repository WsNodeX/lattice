"""Exceptions raised by the :mod:`lattice` package."""

from __future__ import annotations

__all__ = ["LatticeError", "IncompatibleFilterError"]


class LatticeError(Exception):
    """Base class for all errors raised by ``lattice``."""


class IncompatibleFilterError(LatticeError):
    """Raised when two filters/sketches cannot be combined.

    Combinable structures (Bloom filters, Count-Min sketches, HyperLogLog
    registers) must share their size, hash count and seed; otherwise merging
    them would be meaningless.
    """

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason
