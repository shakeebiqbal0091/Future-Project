"""
Calculator Tool Implementation for Agent Executor.
Provides arithmetic operations for agents.
"""

import re
from typing import Dict, Any, Union
from decimal import Decimal, getcontext, ROUND_HALF_UP

from pydantic import BaseModel, Field
from app.core.tools import ToolInterface, ToolSchema, ToolParameter


class CalculatorOperation(str, Enum):
    """Supported calculator operations."""
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"
    POWER = "power"
    SQRT = "sqrt"
    PERCENT = "percent"


class CalculatorInput(BaseModel):
    """Input schema for calculator tool."""

    operation: CalculatorOperation = Field(
        ...,
        description="Arithmetic operation to perform"
    )
    a: Union[float, int, Decimal] = Field(
        ...,
        description="First operand"
    )
    b: Optional[Union[float, int, Decimal]] = Field(
        None,
        description="Second operand (required for binary operations)"
    )
    precision: int = Field(
        default=10,
        ge=0,
        le=50,
        description="Number of decimal places for result"
    )


class CalculatorTool(ToolInterface):
    """Calculator tool for arithmetic operations."""

    def __init__(self):
        super().__init__(
            name="calculator",
            description="Performs arithmetic operations with high precision",
            parameters=self._get_parameters()
        )

    def _get_parameters(self) -> Dict[str, ToolParameter]:
        """Get tool parameters."""
        return {
            "operation": ToolParameter(
                name="operation",
                type="string",
                description="Arithmetic operation to perform",
                required=True,
                enum=[op.value for op in CalculatorOperation]
            ),
            "a": ToolParameter(
                name="a",
                type="number",
                description="First operand",
                required=True
            ),
            "b": ToolParameter(
                name="b",
                type="number",
                description="Second operand (required for binary operations)",
                required=False
            ),
            "precision": ToolParameter(
                name="precision",
                type="integer",
                description="Number of decimal places for result",
                required=False,
                min=0,
                max=50,
                default=10
            )
        }

    def _validate_input(self, arguments: Dict[str, Any]) -> CalculatorInput:
        """Validate and parse input arguments."""
        try:
            input_data = CalculatorInput(**arguments)
            return input_data
        except Exception as e:
            raise ValueError(f"Invalid calculator input: {str(e)}")

    def _set_precision(self, precision: int):
        """Set decimal precision context."""
        getcontext().prec = precision
        getcontext().rounding = ROUND_HALF_UP

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute calculator operation.

        Args:
            arguments: Dictionary containing operation and operands

        Returns:
            Dictionary with result and operation details

        Raises:
            ValueError: If invalid operation or operands
        """
        # Validate input
        input_data = self._validate_input(arguments)
        self._set_precision(input_data.precision)

        # Perform operation
        try:
            if input_data.operation == CalculatorOperation.ADD:
                result = self._add(input_data.a, input_data.b)

            elif input_data.operation == CalculatorOperation.SUBTRACT:
                result = self._subtract(input_data.a, input_data.b)

            elif input_data.operation == CalculatorOperation.MULTIPLY:
                result = self._multiply(input_data.a, input_data.b)

            elif input_data.operation == CalculatorOperation.DIVIDE:
                result = self._divide(input_data.a, input_data.b)

            elif input_data.operation == CalculatorOperation.POWER:
                result = self._power(input_data.a, input_data.b)

            elif input_data.operation == CalculatorOperation.SQRT:
                result = self._sqrt(input_data.a)

            elif input_data.operation == CalculatorOperation.PERCENT:
                result = self._percent(input_data.a)

            else:
                raise ValueError(f"Unsupported operation: {input_data.operation}")

            return {
                "operation": input_data.operation.value,
                "operands": [float(input_data.a), float(input_data.b)] if input_data.b is not None else [float(input_data.a)],
                "result": float(result),
                "precision": input_data.precision,
                "timestamp": str(datetime.utcnow())
            }

        except Exception as e:
            raise ValueError(f"Calculation error: {str(e)}")

    def _add(self, a: Union[float, int, Decimal], b: Union[float, int, Decimal]) -> Decimal:
        """Add two numbers."""
        if b is None:
            raise ValueError("Second operand 'b' is required for addition")
        return Decimal(a) + Decimal(b)

    def _subtract(self, a: Union[float, int, Decimal], b: Union[float, int, Decimal]) -> Decimal:
        """Subtract two numbers."""
        if b is None:
            raise ValueError("Second operand 'b' is required for subtraction")
        return Decimal(a) - Decimal(b)

    def _multiply(self, a: Union[float, int, Decimal], b: Union[float, int, Decimal]) -> Decimal:
        """Multiply two numbers."""
        if b is None:
            raise ValueError("Second operand 'b' is required for multiplication")
        return Decimal(a) * Decimal(b)

    def _divide(self, a: Union[float, int, Decimal], b: Union[float, int, Decimal]) -> Decimal:
        """Divide two numbers."""
        if b is None:
            raise ValueError("Second operand 'b' is required for division")
        if Decimal(b) == 0:
            raise ValueError("Division by zero")
        return Decimal(a) / Decimal(b)

    def _power(self, a: Union[float, int, Decimal], b: Union[float, int, Decimal]) -> Decimal:
        """Raise a to the power of b."""
        if b is None:
            raise ValueError("Second operand 'b' is required for power operation")
        return Decimal(a) ** Decimal(b)

    def _sqrt(self, a: Union[float, int, Decimal]) -> Decimal:
        """Calculate square root."""
        if Decimal(a) < 0:
            raise ValueError("Cannot calculate square root of negative number")
        return Decimal(a).sqrt()

    def _percent(self, a: Union[float, int, Decimal]) -> Decimal:
        """Calculate percentage."""
        return Decimal(a) / Decimal(100)