"""Thin Amadeus Self-Service client with cached OAuth token.

Docs: https://developers.amadeus.com/self-service

Two-tier base URL (test vs production) selected by AMADEUS_ENV. The access
token is cached in-process with a 30-second safety margin so most requests
skip the auth round-trip.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.config import get_settings


class AmadeusError(Exception):
    def __init__(self, status: int, message: str, body: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.body = body


class AmadeusClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._client_id = settings.amadeus_client_id
        self._client_secret = settings.amadeus_client_secret
        self._base_url = (
            "https://api.amadeus.com" if settings.amadeus_env == "production"
            else "https://test.api.amadeus.com"
        )
        self._token: str | None = None
        self._expires_at: float = 0.0

    @property
    def is_configured(self) -> bool:
        return bool(self._client_id and self._client_secret)

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        if not self.is_configured:
            raise AmadeusError(503, "Amadeus is not configured. Set AMADEUS_CLIENT_ID/SECRET.")
        if self._token and self._expires_at > time.time() + 30:
            return self._token

        r = await client.post(
            f"{self._base_url}/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if r.status_code != 200:
            raise AmadeusError(r.status_code, "Amadeus auth failed", r.text)
        data = r.json()
        self._token = data["access_token"]
        self._expires_at = time.time() + int(data.get("expires_in", 1800))
        return self._token

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token = await self._get_token(client)
            clean = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
            r = await client.get(
                f"{self._base_url}{path}",
                params=clean,
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code != 200:
                raise AmadeusError(r.status_code, f"Amadeus {path} {r.status_code}", r.text)
            return r.json()

    async def resolve_iata(self, keyword: str, sub_type: str = "CITY,AIRPORT") -> str | None:
        data = await self.get(
            "/v1/reference-data/locations",
            {"keyword": keyword, "subType": sub_type, "page[limit]": 1},
        )
        items = data.get("data") or []
        return items[0].get("iataCode") if items else None


amadeus_client = AmadeusClient()
