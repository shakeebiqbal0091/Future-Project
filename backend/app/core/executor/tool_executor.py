import json
import logging
from typing import Dict, Any, Optional, List, Type
from abc import ABC, abstractmethod
from pydantic import BaseModel
from app.models.models import ToolEnum

logger = logging.getLogger(__name__)


class ToolBase(ABC):
    """Base class for all tools."""

    name: str
    description: str
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]

    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given input."""
        pass

    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate tool input."""
        pass

    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """Return Pydantic schema for tool parameters."""
        pass


class CalculatorTool(ToolBase):
    name = "calculator"
    description = "Performs arithmetic operations"

    class InputSchema(BaseModel):
        operation: str  # add, subtract, multiply, divide
        a: float
        b: float

    class OutputSchema(BaseModel):
        result: float
        operation: str
        a: float
        b: float
        execution_time_ms: int

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute calculator operation."""
        operation = input_data["operation"]
        a = input_data["a"]
        b = input_data["b"]

        start_time = self._current_millis()

        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                raise ValueError("Cannot divide by zero")
            result = a / b
        else:
            raise ValueError(f"Unknown operation: {operation}")

        execution_time = self._current_millis() - start_time

        return {
            "result": result,
            "operation": operation,
            "a": a,
            "b": b,
            "execution_time_ms": execution_time
        }

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate calculator input."""
        try:
            self.InputSchema(**input_data)
            return True
        except Exception as e:
            logger.error(f"Calculator input validation failed: {e}")
            return False

    def parameters_schema(self) -> Dict[str, Any]:
        """Return Pydantic schema for calculator parameters."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"]
                },
                "a": {"type": "number"},
                "b": {"type": "number"}
            },
            "required": ["operation", "a", "b"]
        }

    def _current_millis(self) -> int:
        """Get current time in milliseconds."""
        import time
        return int(round(time.time() * 1000))


class HTTPRequestTool(ToolBase):
    name = "http_request"
    description = "Make HTTP API calls"

    class InputSchema(BaseModel):
        method: str  # GET, POST, PUT, DELETE
        url: str
        headers: Optional[Dict[str, str]] = None
        body: Optional[Dict[str, Any]] = None
        timeout: Optional[int] = 30

    class OutputSchema(BaseModel):
        status_code: int
        headers: Dict[str, str]
        body: Dict[str, Any]
        execution_time_ms: int

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute HTTP request."""
        import httpx
        import time

        method = input_data["method"].upper()
        url = input_data["url"]
        headers = input_data.get("headers", {})
        body = input_data.get("body")
        timeout = input_data.get("timeout", 30)

        start_time = int(round(time.time() * 1000))

        # Security: Validate URL
        if not self._is_safe_url(url):
            raise ValueError("Unsafe URL detected")

        # Security: Limit headers
        allowed_headers = {"Content-Type", "Accept", "Authorization"}
        filtered_headers = {k: v for k, v in headers.items() if k in allowed_headers}

        # Security: Limit body size
        if body and len(json.dumps(body)) > 1024 * 100:  # 100KB limit
            raise ValueError("Request body too large")

        # Make the request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method,
                    url,
                    headers=filtered_headers,
                    json=body,
                    timeout=timeout
                )

                execution_time = int(round(time.time() * 1000)) - start_time

                return {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response.json() if response.is_json else {},
                    "execution_time_ms": execution_time
                }
            except Exception as e:
                execution_time = int(round(time.time() * 1000)) - start_time
                return {
                    "error": str(e),
                    "execution_time_ms": execution_time
                }

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate HTTP request input."""
        try:
            self.InputSchema(**input_data)
            return True
        except Exception as e:
            logger.error(f"HTTP request input validation failed: {e}")
            return False

    def parameters_schema(self) -> Dict[str, Any]:
        """Return Pydantic schema for HTTP request parameters."""
        return {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE"]
                },
                "url": {"type": "string", "format": "uri"},
                "headers": {
                    "type": "object",
                    "additionalProperties": {"type": "string"}
                },
                "body": {
                    "type": "object"
                },
                "timeout": {"type": "integer", "minimum": 1, "maximum": 300}
            },
            "required": ["method", "url"]
        }

    def _is_safe_url(self, url: str) -> bool:
        """Check if URL is safe (basic validation)."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False

        # Allow only HTTP/HTTPS
        if parsed.scheme not in ["http", "https"]:
            return False

        # Block private IP ranges
        private_networks = [
            "10.", "172.16.", "192.168.", "127.",
            "169.254.", "::1", "fe80::"
        ]

        for network in private_networks:
            if parsed.netloc.startswith(network):
                return False

        return True


class EmailSendTool(ToolBase):
    name = "email_send"
    description = "Send email via connected account"

    class InputSchema(BaseModel):
        to: str
        subject: str
        body: str
        cc: Optional[str] = None
        bcc: Optional[str] = None

    class OutputSchema(BaseModel):
        message_id: str
        to: List[str]
        subject: str
        status: str
        execution_time_ms: int

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute email sending."""
        import smtplib
        import time
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        to = input_data["to"]
        subject = input_data["subject"]
        body = input_data["body"]
        cc = input_data.get("cc")
        bcc = input_data.get("bcc")

        start_time = int(round(time.time() * 1000))

        # Create message
        msg = MIMEMultipart()
        msg["From"] = "noreply@agentflow.com"
        msg["To"] = to
        if cc:
            msg["Cc"] = cc
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "html" if "<" in body else "plain"))

        # Send email (mock implementation - replace with real SMTP)
        # In production, this would use a proper email service
        execution_time = int(round(time.time() * 1000)) - start_time

        return {
            "message_id": f"msg-{int(time.time())}",
            "to": [to] + ([cc] if cc else []) + ([bcc] if bcc else []),
            "subject": subject,
            "status": "sent",
            "execution_time_ms": execution_time
        }

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate email input."""
        try:
            self.InputSchema(**input_data)
            return True
        except Exception as e:
            logger.error(f"Email input validation failed: {e}")
            return False

    def parameters_schema(self) -> Dict[str, Any]:
        """Return Pydantic schema for email parameters."""
        return {
            "type": "object",
            "properties": {
                "to": {"type": "string", "format": "email"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
                "cc": {"type": "string", "format": "email"},
                "bcc": {"type": "string", "format": "email"}
            },
            "required": ["to", "subject", "body"]
        }


class SlackPostTool(ToolBase):
    name = "slack_post"
    description = "Post message to Slack"

    class InputSchema(BaseModel):
        channel: str
        text: str
        thread_ts: Optional[str] = None

    class OutputSchema(BaseModel):
        channel: str
        text: str
        timestamp: str
        status: str
        execution_time_ms: int

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Slack post."""
        import time
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError

        channel = input_data["channel"]
        text = input_data["text"]
        thread_ts = input_data.get("thread_ts")

        start_time = int(round(time.time() * 1000))

        # Mock implementation (replace with real Slack client)
        # client = WebClient(token=settings.SLACK_BOT_TOKEN)
        # try:
        #     response = client.chat_postMessage(
        #         channel=channel,
        #         text=text,
        #         thread_ts=thread_ts
        #     )
        #     return {
        #         "channel": channel,
        #         "text": text,
        #         "timestamp": response["ts"],
        #         "status": "success",
        #         "execution_time_ms": int(round(time.time() * 1000)) - start_time
        #     }
        # except SlackApiError as e:
        #     return {
        #         "error": str(e),
        #         "execution_time_ms": int(round(time.time() * 1000)) - start_time
        #     }

        # Mock response for now
        execution_time = int(round(time.time() * 1000)) - start_time
        return {
            "channel": channel,
            "text": text,
            "timestamp": f"t{int(time.time())}",
            "status": "success",
            "execution_time_ms": execution_time
        }

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate Slack input."""
        try:
            self.InputSchema(**input_data)
            return True
        except Exception as e:
            logger.error(f"Slack input validation failed: {e}")
            return False

    def parameters_schema(self) -> Dict[str, Any]:
        """Return Pydantic schema for Slack parameters."""
        return {
            "type": "object",
            "properties": {
                "channel": {"type": "string"},
                "text": {"type": "string"},
                "thread_ts": {"type": "string"}
            },
            "required": ["channel", "text"]
        }


class ToolExecutor:
    """Tool executor that manages and executes available tools."""

    def __init__(self):
        self.tools = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Register default tools."""
        self.register_tool(CalculatorTool())
        self.register_tool(HTTPRequestTool())
        self.register_tool(EmailSendTool())
        self.register_tool(SlackPostTool())

    def register_tool(self, tool: ToolBase):
        """Register a new tool."""
        if tool.name in self.tools:
            logger.warning(f"Tool {tool.name} already registered, overwriting")
        self.tools[tool.name] = tool

    def get_tool(self, tool_name: str) -> Optional[ToolBase]:
        """Get a tool by name."""
        return self.tools.get(tool_name)

    def get_all_tools(self) -> Dict[str, ToolBase]:
        """Get all registered tools."""
        return self.tools.copy()

    async def execute_tool(
        self,
        agent: Agent,
        tool_call: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool call from Claude."""
        tool_name = tool_call["name"]
        tool_input = tool_call["input"]

        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Validate tool permissions
        if tool_name not in agent.tools:
            raise PermissionError(f"Tool {tool_name} not permitted for this agent")

        # Validate input
        if not tool.validate_input(tool_input):
            raise ValueError(f"Invalid input for tool {tool_name}")

        # Execute tool
        result = tool.execute(tool_input)

        return result

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools."""
        tools = []
        for tool_name, tool in self.tools.items():
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters_schema()
            })
        return tools


# Initialize global tool executor
global_tool_executor = ToolExecutor()

def get_tool_executor() -> ToolExecutor:
    """Get the global tool executor instance."""
    return global_tool_executor