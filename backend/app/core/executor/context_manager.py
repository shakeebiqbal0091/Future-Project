import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.models.models import Agent, Task

logger = logging.getLogger(__name__)


class ContextManager:
    """Manage execution context for agents, including conversation history and state."""

    def __init__(
        self,
        max_history_length: int = 20,
        conversation_ttl_minutes: int = 60
    ):
        self.max_history_length = max_history_length
        self.conversation_ttl_minutes = conversation_ttl_minutes
        self.context_store = {}

    def initialize_context(
        self,
        agent: Agent,
        user_input: Dict[str, Any],
        previous_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Initialize execution context."""
        context = {
            "agent_id": agent.id,
            "organization_id": agent.organization_id,
            "user_input": user_input,
            "conversation_history": [],
            "tool_results": {},
            "session_start": datetime.utcnow().isoformat(),
            "ttl": (datetime.utcnow() + timedelta(minutes=self.conversation_ttl_minutes)).isoformat(),
            "state": {
                "step": 0,
                "status": "initialized",
                "error_count": 0
            }
        }

        # Add previous context if provided
        if previous_context:
            context["conversation_history"] = previous_context.get("conversation_history", [])
            context["tool_results"] = previous_context.get("tool_results", {})
            context["state"] = previous_context.get("state", context["state"])

        return context

    def update_context(
        self,
        context: Dict[str, Any],
        message: Dict[str, Any],
        tool_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update context with new message or tool results."""
        # Add message to conversation history
        context["conversation_history"].append(message)

        # Limit history length
        if len(context["conversation_history"]) > self.max_history_length:
            context["conversation_history"] = context["conversation_history"][-self.max_history_length:]

        # Update tool results
        if tool_results:
            for tool_name, result in tool_results.items():
                if tool_name not in context["tool_results"]:
                    context["tool_results"][tool_name] = {}
                context["tool_results"][tool_name].update(result)

        # Update state
        context["state"]["step"] += 1
        context["state"]["last_updated"] = datetime.utcnow().isoformat()

        return context

    def get_context_summary(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary of context for debugging."""
        return {
            "agent_id": context.get("agent_id"),
            "organization_id": context.get("organization_id"),
            "conversation_length": len(context.get("conversation_history", [])),
            "tool_results_count": len(context.get("tool_results", {})),
            "session_age_minutes": self._calculate_session_age(context),
            "state": context.get("state")
        }

    def is_context_valid(self, context: Dict[str, Any]) -> bool:
        """Check if context is still valid (not expired)."""
        ttl = context.get("ttl")
        if not ttl:
            return False

        ttl_time = datetime.fromisoformat(tl.replace("Z", "+00:00"))
        return datetime.utcnow() < ttl_time

    def cleanup_expired_contexts(self):
        """Clean up expired contexts."""
        current_time = datetime.utcnow()
        expired_contexts = []

        for context_id, context in self.context_store.items():
            ttl = context.get("ttl")
            if ttl:
                ttl_time = datetime.fromisoformat(tl.replace("Z", "+00:00"))
                if current_time > ttl_time:
                    expired_contexts.append(context_id)

        for context_id in expired_contexts:
            del self.context_store[context_id]
            logger.info(f"Cleaned up expired context: {context_id}")

        return len(expired_contexts)

    def save_context(self, context_id: str, context: Dict[str, Any]):
        """Save context for later retrieval."""
        self.context_store[context_id] = context

    def load_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """Load saved context."""
        context = self.context_store.get(context_id)
        if context and self.is_context_valid(context):
            return context
        return None

    def _calculate_session_age(self, context: Dict[str, Any]) -> float:
        """Calculate session age in minutes."""
        session_start = context.get("session_start")
        if not session_start:
            return 0.0

        session_time = datetime.fromisoformat(session_start.replace("Z", "+00:00"))
        return (datetime.utcnow() - session_time).total_seconds() / 60


# Global context manager instance
context_manager = ContextManager()

def get_context_manager() -> ContextManager:
    """Get the global context manager instance."""
    return context_manager