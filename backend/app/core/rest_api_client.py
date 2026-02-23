"""
REST API Client for the AI Agent Orchestration Platform

A comprehensive HTTP client with support for various authentication methods,
request/response transformation, error handling, and monitoring.
"""

import logging
import time
import typing as t
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin, urlencode

import httpx
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class RESTAPISettings(BaseSettings):
    """Configuration settings for REST API client"""

    base_url: str = Field(..., description="Base URL for the API")
    timeout: int = Field(30, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retries")
    retry_delay: int = Field(1, description="Base delay between retries in seconds")
    retry_multiplier: float = Field(2.0, description="Multiplier for exponential backoff")
    retry_statuses: List[int] = Field([429, 500, 502, 503, 504],
                                   description="HTTP status codes that should trigger retries")
    rate_limit_enabled: bool = Field(True, description="Enable rate limiting")
    rate_limit_window: int = Field(60, description="Rate limit window in seconds")
    rate_limit_max_calls: int = Field(60, description="Maximum calls per window")


class AuthenticationMethod(BaseModel):
    """Base authentication method"""

    type: str

    def apply(self, request: httpx.Request) -> httpx.Request:
        """Apply authentication to request"""
        raise NotImplementedError


class APIKeyAuth(AuthenticationMethod):
    """API Key authentication"""

    type: str = Field("api_key", const=True)
    key: str = Field(..., description="API key value")
    key_name: str = Field("Authorization", description="Header name for API key")
    prefix: Optional[str] = Field(None, description="Prefix for API key (e.g., 'Bearer ')")
    in_header: bool = Field(True, description="Send in header")
    in_query: bool = Field(False, description="Send in query parameter")

    def apply(self, request: httpx.Request) -> httpx.Request:
        """Apply API key authentication"""
        if self.in_header:
            auth_value = f"{self.prefix} {self.key}" if self.prefix else self.key
            request.headers[self.key_name] = auth_value

        if self.in_query:
            url = request.url.copy_with(query={
                **request.url.query,
                self.key_name: self.key
            })
            request.url = url

        return request


class OAuth2Auth(AuthenticationMethod):
    """OAuth2 authentication"""

    type: str = Field("oauth2", const=True)
    access_token: str = Field(..., description="Access token")
    token_type: str = Field("Bearer", description="Token type")

    def apply(self, request: httpx.Request) -> httpx.Request:
        """Apply OAuth2 authentication"""
        request.headers["Authorization"] = f"{self.token_type} {self.access_token}"
        return request


class BasicAuth(AuthenticationMethod):
    """Basic authentication"""

    type: str = Field("basic", const=True)
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")

    def apply(self, request: httpx.Request) -> httpx.Request:
        """Apply Basic authentication"""
        import base64
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        request.headers["Authorization"] = f"Basic {encoded}"
        return request


class BearerTokenAuth(AuthenticationMethod):
    """Bearer token authentication"""

    type: str = Field("bearer", const=True)
    token: str = Field(..., description="Bearer token")

    def apply(self, request: httpx.Request) -> httpx.Request:
        """Apply Bearer token authentication"""
        request.headers["Authorization"] = f"Bearer {self.token}"
        return request


class RateLimitState:
    """State for rate limiting"""

    def __init__(self):
        self.window_start: Optional[datetime] = None
        self.calls: int = 0
        self.lock_time: Optional[datetime] = None


class RESTAPIClient:
    """
    Generic REST API client with comprehensive features

    Features:
    - Multiple authentication methods
    - Request/response transformation
    - Error handling and retry logic
    - Timeout and rate limiting configuration
    - Request/response logging and monitoring
    - Request/response validation
    """

    def __init__(
        self,
        settings: RESTAPISettings,
        auth_method: Optional[AuthenticationMethod] = None,
        default_headers: Optional[Dict[str, str]] = None,
        request_transformers: Optional[List[callable]] = None,
        response_transformers: Optional[List[callable]] = None,
    ):
        self.settings = settings
        self.auth_method = auth_method
        self.default_headers = default_headers or {}
        self.request_transformers = request_transformers or []
        self.response_transformers = response_transformers or []

        # Rate limiting state
        self.rate_limit_state = RateLimitState()

        # Initialize HTTP client
        self.client = httpx.AsyncClient(
            timeout=self.settings.timeout,
            headers=self.default_headers,
            base_url=self.settings.base_url
        )

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        **kwargs
    ) -> httpx.Response:
        """Make an HTTP request with comprehensive error handling"""

        # Apply request transformers
        for transformer in self.request_transformers:
            path, params, json, data, headers, files = transformer(
                method, path, params, json, data, headers, files
            )

        # Build request
        url = urljoin(self.settings.base_url, path)
        if params:
            url = f"{url}?{urlencode(params)}"

        request = httpx.Request(
            method=method,
            url=url,
            json=json,
            data=data,
            headers=headers,
            files=files,
            **kwargs
        )

        # Apply authentication
        if self.auth_method:
            request = self.auth_method.apply(request)

        # Apply rate limiting if enabled
        if self.settings.rate_limit_enabled:
            await self._apply_rate_limit()

        # Make request with retry logic
        return await self._make_request_with_retries(request, timeout)

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> httpx.Response:
        """GET request"""
        return await self.request("GET", path, params=params, **kwargs)

    async def post(
        self,
        path: str,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        files: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> httpx.Response:
        """POST request"""
        return await self.request("POST", path, json=json, data=data, files=files, **kwargs)

    async def put(
        self,
        path: str,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        **kwargs
    ) -> httpx.Response:
        """PUT request"""
        return await self.request("PUT", path, json=json, data=data, **kwargs)

    async def delete(
        self,
        path: str,
        **kwargs
    ) -> httpx.Response:
        """DELETE request"""
        return await self.request("DELETE", path, **kwargs)

    async def patch(
        self,
        path: str,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        **kwargs
    ) -> httpx.Response:
        """PATCH request"""
        return await self.request("PATCH", path, json=json, data=data, **kwargs)

    async def _make_request_with_retries(
        self,
        request: httpx.Request,
        timeout: Optional[int] = None
    ) -> httpx.Response:
        """Make request with retry logic"""

        retry_count = 0
        last_error: Optional[Exception] = None

        while retry_count <= self.settings.max_retries:
            try:
                # Log request
                logger.debug(f"Making request: {request.method} {request.url}")

                # Make the request
                response = await self.client.send(request, timeout=timeout or self.settings.timeout)

                # Log response
                logger.debug(f"Response received: {response.status_code} {response.url}")

                # Handle rate limiting response
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        await self._apply_rate_limit(
                            delay=int(retry_after),
                            force=True
                        )
                        retry_count += 1
                        continue

                # Handle server errors
                if response.status_code in self.settings.retry_statuses:
                    retry_count += 1
                    if retry_count <= self.settings.max_retries:
                        await self._apply_retry_delay(retry_count)
                        continue

                # Return response if successful or non-retryable error
                return response

            except httpx.TimeoutException as e:
                last_error = e
                retry_count += 1
                if retry_count <= self.settings.max_retries:
                    await self._apply_retry_delay(retry_count)
                    continue
            except httpx.RequestError as e:
                last_error = e
                retry_count += 1
                if retry_count <= self.settings.max_retries:
                    await self._apply_retry_delay(retry_count)
                    continue
            except Exception as e:
                last_error = e
                retry_count += 1
                if retry_count <= self.settings.max_retries:
                    await self._apply_retry_delay(retry_count)
                    continue

        # If we've exhausted retries, raise the last error
        if last_error:
            raise last_error
        else:
            raise Exception("Request failed after maximum retries")

    async def _apply_rate_limit(
        self,
        delay: Optional[int] = None,
        force: bool = False
    ):
        """Apply rate limiting"""

        if not self.settings.rate_limit_enabled and not force:
            return

        now = datetime.utcnow()

        # Reset if new window
        if not self.rate_limit_state.window_start or
           (now - self.rate_limit_state.window_start).total_seconds() >= self.settings.rate_limit_window:
            self.rate_limit_state.window_start = now
            self.rate_limit_state.calls = 0
            self.rate_limit_state.lock_time = None

        # Check if we're locked out
        if self.rate_limit_state.lock_time and
           (now - self.rate_limit_state.lock_time).total_seconds() < 60:
            raise Exception("Rate limit exceeded - locked out")

        # Check if we've exceeded the limit
        if self.rate_limit_state.calls >= self.settings.rate_limit_max_calls:
            # Calculate delay if not provided
            if delay is None:
                delay = self.settings.rate_limit_window -
                       (now - self.rate_limit_state.window_start).total_seconds()

            # Apply delay
            logger.debug(f"Rate limit exceeded - sleeping for {delay} seconds")
            await asyncio.sleep(delay)

            # Reset for new window
            self.rate_limit_state.window_start = datetime.utcnow()
            self.rate_limit_state.calls = 0

        # Increment call count
        self.rate_limit_state.calls += 1

    async def _apply_retry_delay(self, retry_count: int):
        """Apply exponential backoff for retries"""
        delay = self.settings.retry_delay * (self.settings.retry_multiplier ** (retry_count - 1))
        logger.debug(f"Retrying in {delay:.2f} seconds...")
        await asyncio.sleep(delay)

    def add_request_transformer(self, transformer: callable):
        """Add a request transformer"""
        self.request_transformers.append(transformer)

    def add_response_transformer(self, transformer: callable):
        """Add a response transformer"""
        self.response_transformers.append(transformer)


# Request/Response transformers

def add_default_headers_transformer(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]],
    json: Optional[Any],
    data: Optional[Any],
    headers: Optional[Dict[str, str]],
    files: Optional[Dict[str, Any]]
) -> t.Tuple[str, Optional[Dict[str, Any]], Optional[Any], Optional[Any], Optional[Dict[str, str]], Optional[Dict[str, Any]]]:
    """Add default headers to request"""
    default_headers = {
        "User-Agent": "AI-Agent-Orchestration-Platform/1.0",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
    }

    if headers:
        headers.update(default_headers)
    else:
        headers = default_headers

    return method, path, params, json, data, headers, files


def add_content_type_transformer(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]],
    json: Optional[Any],
    data: Optional[Any],
    headers: Optional[Dict[str, str]],
    files: Optional[Dict[str, Any]]
) -> t.Tuple[str, Optional[Dict[str, Any]], Optional[Any], Optional[Any], Optional[Dict[str, str]], Optional[Dict[str, Any]]]:
    """Add appropriate Content-Type header"""
    if json and headers and "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"

    if files and headers and "Content-Type" not in headers:
        headers["Content-Type"] = "multipart/form-data"

    return method, path, params, json, data, headers, files