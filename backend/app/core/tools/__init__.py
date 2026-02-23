"""
Agent Tool Framework - Base classes and interfaces for tool execution.
"""

from typing import Any, Dict, Optional, Union, List, Type

from pydantic import BaseModel, Field


class ToolInterface:
    """Base interface for tools."""

    def __init__(self, name: str, description: str, parameters: Dict[str, Any]):
        self.name = name
        self.description = description
        self.parameters = parameters

    async def execute(self, arguments: Dict[str, Any]) -> Any:
        """Execute the tool with given arguments.

        Args:
            arguments: Dictionary containing tool arguments

        Returns:
            Result of the tool execution

        Raises:
            Exception: If tool execution fails
        """
        raise NotImplementedError("Tool must implement execute method")


class ToolSchema(BaseModel):
    """Schema for tool definition."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters schema")
    category: str = Field(default="general", description="Tool category")
    icon: str = Field(default="", description="Icon for UI display")
    enabled_by_default: bool = Field(default=True, description="Whether tool is enabled by default")


class ToolRegistry:
    """Registry for available tools."""

    _tools: Dict[str, Type[ToolInterface]] = {}

    @classmethod
    def register(cls, tool_class: Type[ToolInterface]):
        """Register a tool class."""
        tool_name = tool_class.__name__.replace("Tool", "").lower()
        cls._tools[tool_name] = tool_class
        return tool_class

    @classmethod
    def get_tool(cls, tool_name: str) -> Optional[Type[ToolInterface]]:
        """Get a registered tool class."""
        return cls._tools.get(tool_name)

    @classmethod
    def list_tools(cls) -> List[str]:
        """List all registered tool names."""
        return list(cls._tools.keys())


class ToolParameter(BaseModel):
    """Definition for a tool parameter."""

    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type (string, number, boolean, array, object)")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=True, description="Whether parameter is required")
    default: Optional[Any] = Field(None, description="Default value")
    enum: Optional[List[Any]] = Field(None, description="Allowed values for enum type")
    min: Optional[Union[int, float]] = Field(None, description="Minimum value")
    max: Optional[Union[int, float]] = Field(None, description="Maximum value")
    pattern: Optional[str] = Field(None, description="Regex pattern for string validation")


class ToolCallRequest(BaseModel):
    """Request to execute a tool."""

    tool_name: str = Field(..., description="Name of the tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments for the tool")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Execution context")


class ToolCallResponse(BaseModel):
    """Response from tool execution."""

    success: bool = Field(..., description="Whether execution was successful")
    tool_name: str = Field(..., description="Name of the tool")
    result: Optional[Any] = Field(None, description="Execution result")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    duration_ms: int = Field(..., description="Execution duration in milliseconds")
    tokens_used: Optional[int] = Field(None, description="Tokens used for LLM-assisted execution")


class ToolExecutionError(Exception):
    """Exception raised during tool execution."""

    def __init__(self, tool_name: str, message: str, code: Optional[str] = None):
        super().__init__(message)
        self.tool_name = tool_name
        self.message = message
        self.code = code


class ToolSecurityContext(BaseModel):
    """Security context for tool execution."""

    user_id: str = Field(..., description="User ID")
    organization_id: str = Field(..., description="Organization ID")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    rate_limit: Optional[Dict[str, int]] = Field(None, description="Rate limiting configuration")
    sandbox: bool = Field(default=True, description="Whether to run in sandbox mode")


class ToolAuditLog(BaseModel):
    """Audit log for tool execution."""

    execution_id: str = Field(..., description="Execution ID")
    tool_name: str = Field(..., description="Tool name")
    user_id: str = Field(..., description="User ID")
    organization_id: str = Field(..., description="Organization ID")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments used")
    result: Optional[Any] = Field(None, description="Execution result")
    error: Optional[str] = Field(None, description="Error message if failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Execution timestamp")
    duration_ms: int = Field(..., description="Execution duration")
    ip_address: Optional[str] = Field(None, description="User IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")