"""bcl-python client."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .client import BCLClient, BCLSettings
from .exceptions import BCLOrderNotFoundError, BCLSampleNotFoundError
from .models import (
    BCLOrderSample,
    BCLOrderStatus,
    BCLPatient,
    BCLProject,
    BCLSampleResult,
    BCLSampleStatus,
    BCLStatus,
    BCLTest,
    BCLTestSample,
    validate_metadata_helper,
)

try:
    __version__ = version("bcl-python")
except PackageNotFoundError:  # pragma: no cover — editable install without metadata
    __version__ = "0.1.0"

__all__ = [
    "BCLClient",
    "BCLOrderNotFoundError",
    "BCLOrderSample",
    "BCLOrderStatus",
    "BCLPatient",
    "BCLProject",
    "BCLSampleNotFoundError",
    "BCLSampleResult",
    "BCLSampleStatus",
    "BCLSettings",
    "BCLStatus",
    "BCLTest",
    "BCLTestSample",
    "__version__",
    "validate_metadata_helper",
]
