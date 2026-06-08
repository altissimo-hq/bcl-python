"""BCL Models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from functools import total_ordering
from typing import Any

from pydantic import BaseModel, field_validator


@total_ordering
class OrderedStrEnum(StrEnum):
    """Ordered String Enum class."""

    def __ge__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        members = list(self.__class__)
        return members.index(self) >= members.index(other)

    def __gt__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        members = list(self.__class__)
        return members.index(self) > members.index(other)

    def __le__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        members = list(self.__class__)
        return members.index(self) <= members.index(other)

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        members = list(self.__class__)
        return members.index(self) < members.index(other)


class BCLOrderStatus(OrderedStrEnum):
    """BCL Order Status model."""

    SUBMITTED = "SUBMITTED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"

    @property
    def color(self) -> str:
        """Returns the Bootstrap color class for the kit status."""
        if self == BCLOrderStatus.COMPLETED:
            return "success"
        if self == BCLOrderStatus.PROCESSING:
            return "warning"
        if self == BCLOrderStatus.SUBMITTED:
            return "danger"
        return "secondary"


class BCLSampleStatus(OrderedStrEnum):
    """BCL Sample Status model."""

    CREATED = "CREATED"
    AWAITING_RECEIPT = "AWAITING_RECEIPT"
    CANCELED = "CANCELED"
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    LAB_AND_DATA_DELIVERY_COMPLETED = "LAB_AND_DATA_DELIVERY_COMPLETED"

    @property
    def color(self) -> str:
        """Returns the Bootstrap color class for the kit status."""
        if self == BCLSampleStatus.LAB_AND_DATA_DELIVERY_COMPLETED:
            return "success"
        if self == BCLSampleStatus.RECEIVED:
            return "info"
        if self == BCLSampleStatus.AWAITING_RECEIPT:
            return "warning"
        if self == BCLSampleStatus.CANCELED:
            return "danger"
        return "secondary"


def validate_metadata_helper(value: Any) -> dict[str, Any]:
    """Validate metadata and convert list-of-dicts metadata to a flat dict."""
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, list):
        metadata = {}
        for item in value:
            if not isinstance(item, dict) or "key" not in item or "value" not in item:
                continue
            k = item["key"]
            v = item["value"]
            if isinstance(v, list) and len(v) == 1:
                v = v[0]
            metadata[k] = v
        return metadata
    return {}


class BCLPatient(BaseModel):
    """BCL Patient model."""

    patient_id: str
    sidr_patient_id: str
    files: list[Any]
    last_modified: datetime
    metadata: dict[str, Any]

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, value: Any) -> Any:
        """Validate metadata."""
        return validate_metadata_helper(value)


class BCLProject(BaseModel):
    """BCL Project model."""

    project_key: str
    name: str
    type: str
    organization: str
    metadata: dict[str, Any] = {}

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, value: Any) -> Any:
        """Validate metadata."""
        return validate_metadata_helper(value)


class BCLOrderSample(BaseModel):
    """BCL Order Sample model."""

    sample_id: str
    client_barcode: str
    sidr_sample_id: str
    material_type: str
    original_material_type: str | None = None
    shipping_information: dict[str, Any]
    patient: BCLPatient
    metadata: dict[str, Any]

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, value: Any) -> Any:
        """Validate metadata."""
        return validate_metadata_helper(value)


class BCLSampleResult(BaseModel):
    """BCL Sample Result model."""

    latest: bool
    links: dict[str, Any]
    result_type: str
    result_url_display_text: str
    result_url: str
    result_value: str
    updated_on: datetime
    version: int

    @field_validator("updated_on", mode="after")
    @classmethod
    def validate_aware_datetime(cls, dt: datetime | None) -> datetime | None:
        """Make timezone aware."""
        if isinstance(dt, datetime) and dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt


class BCLStatus(BaseModel):
    """BCL Order Status model."""

    status_key: str
    status_name: str
    timestamp: datetime


class BCLTestSample(BaseModel):
    """BCL Test Sample model."""

    sample_id: str
    sidr_sample_id: str
    test_sample_status: BCLSampleStatus
    status_history: list[BCLStatus]
    client_barcode: str
    results: list[Any]
    last_modified: datetime
    result: str | None = None
    result_code: str | None = None
    result_date: datetime | None = None
    result_description: str | None = None
    result_status: str | None = None

    @field_validator("result_date", mode="after")
    @classmethod
    def validate_aware_datetime(cls, dt: datetime | None) -> datetime | None:
        """Make timezone aware."""
        if isinstance(dt, datetime) and dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt


class BCLTest(BaseModel):
    """BCL Test model."""

    test_code: str
    test_samples: list[BCLTestSample]
