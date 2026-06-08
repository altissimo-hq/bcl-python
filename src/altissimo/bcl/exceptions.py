"""BCL Exceptions."""

from __future__ import annotations


class BCLOrderNotFoundError(Exception):
    """Raised when a BCL Order is not found."""


class BCLSampleNotFoundError(Exception):
    """Raised when a BCL Sample is not found."""
