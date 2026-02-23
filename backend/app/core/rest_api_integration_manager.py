"""
REST API Integration Manager

Manages REST API integrations, including creation, configuration, testing,
and execution of API actions.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings

from app.core.rest_api_client import (
    RESTAPISettings,
    RESTAPIClient,
    AuthenticationMethod,
    APIKeyAuth,
    OAuth2Auth,
    BasicAuth,
    BearerTokenAuth
)
from app.models.models import Integration, IntegrationStatusEnum
from app.schemas.integrations import (
    Integration,
    IntegrationTestResponse,
    IntegrationAction,
    IntegrationActionRequest,
    IntegrationActionResponse
)

logger = logging.getLogger(__name__)


class RESTAPIIntegrationManager:
    """
    Manager for REST API integrations

    Handles:
    - Integration creation and configuration
    - Connection testing and validation
    - Action definition and execution
    - Security and validation
    - Configuration management
    """

    def __init__(self, integration: Integration):
        self.integration = integration
        self.client: Optional[RESTAPIClient] = None
        self.auth_method: Optional[AuthenticationMethod] = None
        self._build_client()

    def _build_client(self):
        """Build REST API client based on integration configuration"""

        # Parse integration config
        config = self.integration.config

        # Build REST API settings
        settings = RESTAPISettings(
            base_url=config.get("base_url", "https://example.com"),
            timeout=config.get("timeout", 30),
            max_retries=config.get("max_retries", 3),
            retry_delay=config.get("retry_delay", 1),
            retry_multiplier=config.get("retry_multiplier", 2.0),
            rate_limit_enabled=config.get("rate_limit_enabled", True),
            rate_limit_window=config.get("rate_limit_window", 60),
            rate_limit_max_calls=config.get("rate_limit_max_calls", 60)
        )

        # Build authentication method
        self.auth_method = self._build_auth_method(config.get("auth", {}))

        # Build client
        self.client = RESTAPIClient(
            settings=settings,
            auth_method=self.auth_method,
            default_headers=config.get("headers", {}),
            request_transformers=[
                self._add_default_headers,
                self._add_content_type
            ]
        )

    def _build_auth_method(self, auth_config: Dict[str, Any]) -> Optional[AuthenticationMethod]:
        """Build authentication method from config"""

        auth_type = auth_config.get("type")

        if not auth_type:
            return None

        if auth_type == "api_key":
            return APIKeyAuth(
                key=auth_config.get("key"),
                key_name=auth_config.get("key_name", "Authorization"),
                prefix=auth_config.get("prefix"),
                in_header=auth_config.get("in_header", True),
                in_query=auth_config.get("in_query", False)
            )

        elif auth_type == "oauth2":
            return OAuth2Auth(
                access_token=auth_config.get("access_token"),
                token_type=auth_config.get("token_type", "Bearer")
            )

        elif auth_type == "basic":
            return BasicAuth(
                username=auth_config.get("username"),
                password=auth_config.get("password")
            )

        elif auth_type == "bearer":
            return BearerTokenAuth(
                token=auth_config.get("token")
            )

        else:
            raise ValueError(f"Unknown authentication type: {auth_type}")

    def test_connection(self) -> IntegrationTestResponse:
        """Test the REST API connection"""

        if not self.client:
            return IntegrationTestResponse(
                success=False,
                message="Client not initialized",
                error="Integration client is not initialized"
            )

        try:
            # Test connection by making a simple GET request to base URL
            test_url = urlparse(self.integration.config["base_url"])
            test_path = "/" if test_url.path == "" else test_url.path

            response = asyncio.run(self.client.get(test_path))

            if response.status_code >= 200 and response.status_code < 300:
                # Update integration status
                self._update_integration_status(IntegrationStatusEnum.connected)

                return IntegrationTestResponse(
                    success=True,
                    message=f"Connection successful: {response.status_code} {response.reason_phrase}",
                    output={
                        "status_code": response.status_code,
                        "reason": response.reason_phrase,
                        "url": str(response.url),
                        "headers": dict(response.headers),
                    }
                )
            else:
                # Update integration status
                self._update_integration_status(IntegrationStatusEnum.error)

                return IntegrationTestResponse(
                    success=False,
                    message=f"Connection failed: {response.status_code} {response.reason_phrase}",
                    error=f"HTTP {response.status_code}: {response.reason_phrase}"
                )

        except Exception as e:
            # Update integration status
            self._update_integration_status(IntegrationStatusEnum.error)

            return IntegrationTestResponse(
                success=False,
                message=f"Connection test failed: {str(e)}",
                error=str(e)
            )

    def get_available_actions(self) -> List[IntegrationAction]:
        """Get available actions for REST API integration"""

        # Define common REST API actions
        actions = [
            IntegrationAction(
                name="get",
                description="Make a GET request",
                parameters={
                    "path": "string (endpoint path)",
                    "params": "object (query parameters)",
                    "headers": "object (request headers)",
                    "timeout": "number (timeout in seconds)"
                }
            ),
            IntegrationAction(
                name="post",
                description="Make a POST request",
                parameters={
                    "path": "string (endpoint path)",
                    "json": "object (request body as JSON)",
                    "data": "object (form data)",
                    "headers": "object (request headers)",
                    "timeout": "number (timeout in seconds)"
                }
            ),
            IntegrationAction(
                name="put",
                description="Make a PUT request",
                parameters={
                    "path": "string (endpoint path)",
                    "json": "object (request body as JSON)",
                    "data": "object (form data)",
                    "headers": "object (request headers)",
                    "timeout": "number (timeout in seconds)"
                }
            ),
            IntegrationAction(
                name="patch",
                description="Make a PATCH request",
                parameters={
                    "path": "string (endpoint path)",
                    "json": "object (request body as JSON)",
                    "data": "object (form data)",
                    "headers": "object (request headers)",
                    "timeout": "number (timeout in seconds)"
                }
            ),
            IntegrationAction(
                name="delete",
                description="Make a DELETE request",
                parameters={
                    "path": "string (endpoint path)",
                    "params": "object (query parameters)",
                    "headers": "object (request headers)",
                    "timeout": "number (timeout in seconds)"
                }
            ),
        ]

        return actions

    async def execute_action(
        self,
        action_name: str,
        params: Dict[str, Any]
    ) -> IntegrationActionResponse:
        """Execute a REST API action"""

        if not self.client:
            return IntegrationActionResponse(
                success=False,
                message="Client not initialized",
                error="Integration client is not initialized"
            )

        try:
            # Execute action based on name
            if action_name == "get":
                return await self._execute_get(params)
            elif action_name == "post":
                return await self._execute_post(params)
            elif action_name == "put":
                return await self._execute_put(params)
            elif action_name == "patch":
                return await self._execute_patch(params)
            elif action_name == "delete":
                return await self._execute_delete(params)
            else:
                return IntegrationActionResponse(
                    success=False,
                    message=f"Unknown action: {action_name}",
                    error=f"Action '{action_name}' is not supported"
                )

        except Exception as e:
            return IntegrationActionResponse(
                success=False,
                message=f"Action '{action_name}' execution failed",
                error=str(e)
            )

    async def _execute_get(self, params: Dict[str, Any]) -> IntegrationActionResponse:
        """Execute GET request"""

        path = params.get("path")
        if not path:
            return IntegrationActionResponse(
                success=False,
                message="Missing required parameter: path",
                error="Path parameter is required for GET request"
            )

        try:
            response = await self.client.get(
                path,
                params=params.get("params"),
                headers=params.get("headers"),
                timeout=params.get("timeout")
            )

            return self._build_action_response(response)

        except Exception as e:
            return IntegrationActionResponse(
                success=False,
                message=f"GET request failed: {str(e)}",
                error=str(e)
            )

    async def _execute_post(self, params: Dict[str, Any]) -> IntegrationActionResponse:
        """Execute POST request"""

        path = params.get("path")
        if not path:
            return IntegrationActionResponse(
                success=False,
                message="Missing required parameter: path",
                error="Path parameter is required for POST request"
            )

        try:
            response = await self.client.post(
                path,
                json=params.get("json"),
                data=params.get("data"),
                headers=params.get("headers"),
                timeout=params.get("timeout")
            )

            return self._build_action_response(response)

        except Exception as e:
            return IntegrationActionResponse(
                success=False,
                message=f"POST request failed: {str(e)}",
                error=str(e)
            )

    async def _execute_put(self, params: Dict[str, Any]) -> IntegrationActionResponse:
        """Execute PUT request"""

        path = params.get("path")
        if not path:
            return IntegrationActionResponse(
                success=False,
                message="Missing required parameter: path",
                error="Path parameter is required for PUT request"
            )

        try:
            response = await self.client.put(
                path,
                json=params.get("json"),
                data=params.get("data"),
                headers=params.get("headers"),
                timeout=params.get("timeout")
            )

            return self._build_action_response(response)

        except Exception as e:
            return IntegrationActionResponse(
                success=False,
                message=f"PUT request failed: {str(e)}",
                error=str(e)
            )

    async def _execute_patch(self, params: Dict[str, Any]) -> IntegrationActionResponse:
        """Execute PATCH request"""

        path = params.get("path")
        if not path:
            return IntegrationActionResponse(
                success=False,
                message="Missing required parameter: path",
                error="Path parameter is required for PATCH request"
            )

        try:
            response = await self.client.patch(
                path,
                json=params.get("json"),
                data=params.get("data"),
                headers=params.get("headers"),
                timeout=params.get("timeout")
            )

            return self._build_action_response(response)

        except Exception as e:
            return IntegrationActionResponse(
                success=False,
                message=f"PATCH request failed: {str(e)}",
                error=str(e)
            )

    async def _execute_delete(self, params: Dict[str, Any]) -> IntegrationActionResponse:
        """Execute DELETE request"""

        path = params.get("path")
        if not path:
            return IntegrationActionResponse(
                success=False,
                message="Missing required parameter: path",
                error="Path parameter is required for DELETE request"
            )

        try:
            response = await self.client.delete(
                path,
                params=params.get("params"),
                headers=params.get("headers"),
                timeout=params.get("timeout")
            )

            return self._build_action_response(response)

        except Exception as e:
            return IntegrationActionResponse(
                success=False,
                message=f"DELETE request failed: {str(e)}",
                error=str(e)
            )

    def _build_action_response(self, response: httpx.Response) -> IntegrationActionResponse:
        """Build action response from HTTP response"""

        # Parse response data
        try:
            data = response.json() if response.headers.get('content-type') == 'application/json' else None
        except:
            data = None

        return IntegrationActionResponse(
            success=response.status_code >= 200 and response.status_code < 300,
            message=f"HTTP {response.status_code}: {response.reason_phrase}",
            output={
                "status_code": response.status_code,
                "reason": response.reason_phrase,
                "url": str(response.url),
                "headers": dict(response.headers),
                "data": data
            }
        )

    def _update_integration_status(self, status: IntegrationStatusEnum):
        """Update integration status"""
        self.integration.status = status
        self.integration.last_sync = datetime.utcnow()

    def _add_default_headers(self, method: str, path: str, params, json, data, headers, files):
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

    def _add_content_type(self, method: str, path: str, params, json, data, headers, files):
        """Add appropriate Content-Type header"""
        if json and headers and "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        if files and headers and "Content-Type" not in headers:
            headers["Content-Type"] = "multipart/form-data"

        return method, path, params, json, data, headers, files