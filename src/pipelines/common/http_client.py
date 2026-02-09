from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.settings import Settings


@dataclass(frozen=True)
class HttpClientConfig:
    timeout_seconds: int
    max_retries: int
    backoff_seconds: float


class HttpClient:
    def __init__(self, config: HttpClientConfig):
        self.config = config
        self.client = httpx.Client(timeout=config.timeout_seconds, follow_redirects=True, trust_env=False)

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
        backoff_seconds: float | None = None,
    ) -> "HttpClient":
        config = HttpClientConfig(
            timeout_seconds=timeout_seconds or settings.request_timeout_seconds,
            max_retries=max_retries if max_retries is not None else settings.http_max_retries,
            backoff_seconds=backoff_seconds or settings.http_backoff_seconds,
        )
        return cls(config)

    def close(self) -> None:
        self.client.close()

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                response = self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt >= self.config.max_retries:
                    break
                sleep_seconds = self.config.backoff_seconds * (2**attempt)
                time.sleep(sleep_seconds)
        raise RuntimeError(f"Request failed after retries for URL: {url}") from last_error

    def get_json(self, url: str, **kwargs: Any) -> Any:
        response = self._request("GET", url, **kwargs)
        content_type = response.headers.get("content-type", "")
        if "json" not in content_type:
            raise ValueError(f"Unexpected content-type '{content_type}' for URL: {url}")
        return response.json()

    def download_bytes(
        self,
        url: str,
        *,
        expected_content_types: list[str] | None = None,
        min_bytes: int = 1,
        **kwargs: Any,
    ) -> tuple[bytes, str]:
        response = self._request("GET", url, **kwargs)
        content_type = response.headers.get("content-type", "")
        if expected_content_types and not any(token in content_type for token in expected_content_types):
            raise ValueError(f"Unexpected content-type '{content_type}' for URL: {url}")
        payload = response.content
        if len(payload) < min_bytes:
            raise ValueError(f"Payload too small ({len(payload)} bytes) for URL: {url}")
        return payload, content_type
