"""BCL GPO Client module."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, cast

import google.auth.transport.requests
import requests
from google.oauth2 import service_account
from requests.exceptions import HTTPError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BCLSettings:
    """Settings for the BCL client."""

    service_account_key: str
    env: str
    host: str
    timeout: int = 30

    @classmethod
    def from_env(cls) -> BCLSettings:
        """Create BCLSettings from environment variables."""
        env = os.environ.get("ENV", "dev")
        service_account_key = os.environ.get("BCL_SERVICE_ACCOUNT_KEY", "")
        if not service_account_key:
            raise ValueError("BCL_SERVICE_ACCOUNT_KEY is not set")
        host = "gpo.broadinstitute.org" if env == "prod" else "gpo-staging.broadinstitute.org"
        return cls(service_account_key=service_account_key, env=env, host=host)

    @property
    def base_url(self) -> str:
        """Get the base URL for the GPO API."""
        return f"https://{self.host}"


class BCLClient:
    """Thin client for the GPO API."""

    def __init__(self, settings: BCLSettings, session: requests.Session | None = None) -> None:
        """Initialize the BCL client."""
        self._settings = settings
        self._session = session or requests.Session()
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "curl/7.81.0",
        }

    @classmethod
    def from_env(cls) -> BCLClient:
        """Create BCLClient from environment variables."""
        return cls(BCLSettings.from_env())

    def _authenticate(self, target_audience: str | None = None) -> None:
        """Authenticate with Google OIDC using the service account key."""
        audience = target_audience or self._settings.base_url
        credentials = service_account.IDTokenCredentials.from_service_account_info(  # type: ignore[no-untyped-call]
            info=json.loads(self._settings.service_account_key),
            target_audience=audience,
        )
        credentials.refresh(google.auth.transport.requests.Request())
        credentials.apply(self._headers)

    def _get_json(self, path: str, *, raise_for_status: bool = True) -> Any:
        """Send a GET request to the GPO API and return JSON response."""
        self._authenticate(self._settings.base_url)
        url = f"{self._settings.base_url}{path}"
        response = self._session.get(url, headers=self._headers, timeout=self._settings.timeout)
        if raise_for_status:
            response.raise_for_status()
        else:
            try:
                response.raise_for_status()
            except HTTPError as exc:
                try:
                    logger.error(exc.response.json())
                except Exception:
                    logger.error(exc)
        return response.json()

    def get_current_user(self) -> dict[str, Any]:
        """Get the current user."""
        return cast(dict[str, Any], self._get_json("/auth"))

    def get_bcl_api_order(self, order_id: str) -> dict[str, Any]:
        """Get a BCL API Order."""
        return cast(dict[str, Any], self._get_json(f"/api/order/{order_id}", raise_for_status=False))

    def get_bcl_api_sample(self, sample_id: str) -> dict[str, Any]:
        """Get a BCL API Sample."""
        return cast(dict[str, Any], self._get_json(f"/api/sample/{sample_id}", raise_for_status=False))

    def list_bcl_api_orders(self) -> list[dict[str, Any]]:
        """List all BCL API Orders, following pagination."""
        items: list[dict[str, Any]] = []
        path = "/api/orders"
        while path:
            data = self._get_json(path)
            items.extend(data.get("items", []))
            path = data.get("paging", {}).get("links", {}).get("next_link")
            if path:
                logger.info(f"BCL orders: fetched {len(items)} so far, fetching next page: {path}")
        logger.info(f"BCL orders: fetched {len(items)} total")
        return items

    def list_bcl_api_samples(self) -> list[dict[str, Any]]:
        """List all BCL API Samples, following pagination."""
        items: list[dict[str, Any]] = []
        path = "/api/samples"
        while path:
            data = self._get_json(path)
            items.extend(data.get("items", []))
            path = data.get("paging", {}).get("links", {}).get("next_link")
            if path:
                logger.info(f"BCL samples: fetched {len(items)} so far, fetching next page: {path}")
        logger.info(f"BCL samples: fetched {len(items)} total")
        return items
