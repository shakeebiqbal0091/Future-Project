"""
HTTP Request Tool Implementation for Agent Executor.
Provides secure HTTP API calling capabilities for agents.
"""

import re
import time
import ssl
from typing import Dict, Any, Optional, Union, List
from urllib.parse import urlparse
from contextlib import asynccontextmanager

import httpx
import certifi
from pydantic import BaseModel, Field, validator
from yarl import URL

from app.core.tools import ToolInterface, ToolSchema, ToolParameter


class HTTPMethod(str, Enum):
    """Supported HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class HTTPRequestInput(BaseModel):
    """Input schema for HTTP request tool."""

    method: HTTPMethod = Field(
        HTTPMethod.GET,
        description="HTTP method to use"
    )
    url: str = Field(
        ...,
        description="URL to request",
        max_length=2000
    )
    headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Request headers"
    )
    params: Dict[str, Union[str, List[str]]] = Field(
        default_factory=dict,
        description="Query parameters"
    )
    data: Optional[Union[Dict[str, Any], List[Any], str]] = Field(
        None,
        description="Request body data (for POST, PUT, PATCH)"
    )
    json: Optional[Union[Dict[str, Any], List[Any]]] = Field(
        None,
        description="JSON request body"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds"
    )
    max_redirects: int = Field(
        default=5,
        ge=0,
        le=20,
        description="Maximum number of redirects"
    )
    verify_ssl: bool = Field(
        default=True,
        description="Whether to verify SSL certificates"
    )
    follow_redirects: bool = Field(
        default=True,
        description="Whether to follow redirects"
    )

    @validator("url")
    def validate_url(cls, v):
        """Validate URL format and security."""
        parsed = urlparse(v)

        # Only allow HTTP and HTTPS schemes
        if parsed.scheme not in ["http", "https"]:
            raise ValueError("Only HTTP and HTTPS URLs are allowed")

        # Basic URL length check
        if len(v) > 2000:
            raise ValueError("URL is too long")

        # Check for suspicious patterns
        if re.search(r"\.\./", v):
            raise ValueError("URL contains invalid path traversal")

        return v


class HTTPRequestTool(ToolInterface):
    """HTTP Request tool for making API calls."""

    def __init__(self):
        super().__init__(
            name="http_request",
            description="Makes secure HTTP API calls with comprehensive validation",
            parameters=self._get_parameters()
        )
        self._client = None

    def _get_parameters(self) -> Dict[str, ToolParameter]:
        """Get tool parameters."""
        return {
            "method": ToolParameter(
                name="method",
                type="string",
                description="HTTP method to use",
                required=True,
                enum=[m.value for m in HTTPMethod]
            ),
            "url": ToolParameter(
                name="url",
                type="string",
                description="URL to request",
                required=True,
                pattern=r"^https?://[\w.-]+(?:\.[\w.-]+)+[\w\-._~:/?#[\]@!$&'()*+,;=.]*$",
                max_length=2000
            ),
            "headers": ToolParameter(
                name="headers",
                type="object",
                description="Request headers",
                required=False
            ),
            "params": ToolParameter(
                name="params",
                type="object",
                description="Query parameters",
                required=False
            ),
            "data": ToolParameter(
                name="data",
                type="object",
                description="Request body data",
                required=False
            ),
            "json": ToolParameter(
                name="json",
                type="object",
                description="JSON request body",
                required=False
            ),
            "timeout": ToolParameter(
                name="timeout",
                type="integer",
                description="Request timeout in seconds",
                required=False,
                min=1,
                max=300,
                default=30
            ),
            "max_redirects": ToolParameter(
                name="max_redirects",
                type="integer",
                description="Maximum number of redirects",
                required=False,
                min=0,
                max=20,
                default=5
            ),
            "verify_ssl": ToolParameter(
                name="verify_ssl",
                type="boolean",
                description="Whether to verify SSL certificates",
                required=False,
                default=True
            ),
            "follow_redirects": ToolParameter(
                name="follow_redirects",
                type="boolean",
                description="Whether to follow redirects",
                required=False,
                default=True
            )
        }

    def _validate_input(self, arguments: Dict[str, Any]) -> HTTPRequestInput:
        """Validate and parse input arguments."""
        try:
            input_data = HTTPRequestInput(**arguments)
            return input_data
        except Exception as e:
            raise ValueError(f"Invalid HTTP request input: {str(e)}")

    @asynccontextmanager
    async def _get_client(self):
        """Get HTTP client with proper configuration."""
        if self._client is None:
            # Configure SSL context with trusted certificates
            ssl_context = ssl.create_default_context(cafile=certifi.where())

            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
                max_redirects=5,
                verify=ssl_context
            )

        try:
            yield self._client
        finally:
            if self._client is not None:
                await self._client.aclose()
                self._client = None

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute HTTP request.

        Args:
            arguments: Dictionary containing request parameters

        Returns:
            Dictionary with response data and metadata

        Raises:
            Exception: If request fails
        """
        start_time = time.time()

        # Validate input
        input_data = self._validate_input(arguments)

        # Sanitize headers (remove sensitive ones)
        headers = input_data.headers.copy()
        headers.pop("Authorization", None)
        headers.pop("Cookie", None)
        headers.pop("Set-Cookie", None)

        # Add security headers
        headers["User-Agent"] = f"AgentFlow-Tool/1.0 (Secure HTTP Client)"
        headers["X-Request-Source"] = "agent-orchestration"
        headers["X-Request-Id"] = str(uuid.uuid4())

        try:
            # Get HTTP client
            async with self._get_client() as client:
                # Build request
                request_kwargs = {
                    "headers": headers,
                    "timeout": input_data.timeout,
                    "follow_redirects": input_data.follow_redirects,
                    "max_redirects": input_data.max_redirects
                }

                if input_data.params:
                    request_kwargs["params"] = input_data.params

                if input_data.data is not None:
                    request_kwargs["data"] = input_data.data

                if input_data.json is not None:
                    request_kwargs["json"] = input_data.json

                # Make request
                response = await client.request(
                    method=input_data.method,
                    url=input_data.url,
                    **request_kwargs
                )

                # Process response
                response_data = {
                    "status_code": response.status_code,
                    "reason": response.reason_phrase,
                    "headers": dict(response.headers),
                    "url": str(response.url),
                    "history": [str(r.url) for r in response.history],
                    "timestamp": str(datetime.utcnow()),
                    "duration_ms": int((time.time() - start_time) * 1000)
                }

                # Handle different content types
                content_type = response.headers.get("content-type", "")

                if "application/json" in content_type:
                    try:
                        response_data["json"] = response.json()
                    except:
                        response_data["text"] = response.text

                elif "text/html" in content_type or "text/plain" in content_type:
                    response_data["text"] = response.text

                else:
                    response_data["content"] = response.content

                return {
                    "success": True,
                    "response": response_data,
                    "metadata": {
                        "tool": "http_request",
                        "method": input_data.method,
                        "url": input_data.url,
                        "duration_ms": response_data["duration_ms"]
                    }
                }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Request timeout",
                "metadata": {
                    "tool": "http_request",
                    "method": input_data.method,
                    "url": input_data.url,
                    "duration_ms": int((time.time() - start_time) * 1000)
                }
            }

        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
                "status_code": e.response.status_code,
                "metadata": {
                    "tool": "http_request",
                    "method": input_data.method,
                    "url": input_data.url,
                    "duration_ms": int((time.time() - start_time) * 1000)
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "tool": "http_request",
                    "method": input_data.method,
                    "url": input_data.url,
                    "duration_ms": int((time.time() - start_time) * 1000)
                }
            }