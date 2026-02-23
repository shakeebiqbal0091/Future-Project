import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.core.integrations.slack_client import SlackClient, SlackIntegrationManager
from app.models.models import Integration, IntegrationStatusEnum
from app.schemas.integrations import Integration, IntegrationTestResponse, IntegrationAction

logger = logging.getLogger(__name__)


class SlackIntegrationManager:
    """Manager for Slack integration operations"""

    def __init__(self, integration: Integration):
        self.integration = integration
        self.client = SlackClient(self._get_bot_token())

    def _get_bot_token(self) -> str:
        """Get the bot token from integration config"""
        return self.integration.config.get("bot_token", "")

    def test_connection(self) -> IntegrationTestResponse:
        """Test the Slack connection"""
        try:
            result = self.client.test_connection()

            # Update integration status based on test result
            self._update_integration_status(success=True)

            return IntegrationTestResponse(
                success=True,
                message="Slack connection successful",
                output={
                    "team": result.get("team", "Unknown"),
                    "user": result.get("user", "Unknown"),
                    "url": result.get("url", "")
                }
            )
        except Exception as e:
            # Update integration status to error
            self._update_integration_status(success=False)

            return IntegrationTestResponse(
                success=False,
                message=f"Slack connection failed: {str(e)}",
                error=str(e)
            )

    def get_available_actions(self) -> List[IntegrationAction]:
        """Get available actions for Slack integration"""
        return [
            IntegrationAction(
                name="post_message",
                description="Post a message to Slack channel",
                parameters={
                    "channel": "string (channel ID or name)",
                    "text": "string",
                    "thread_ts": "string (optional, for replying to threads)",
                    "blocks": "list (optional, Block Kit blocks)"
                }
            ),
            IntegrationAction(
                name="update_message",
                description="Update an existing message",
                parameters={
                    "channel": "string (channel ID)",
                    "ts": "string (timestamp of message to update)",
                    "text": "string",
                    "blocks": "list (optional, Block Kit blocks)"
                }
            ),
            IntegrationAction(
                name="delete_message",
                description="Delete a message",
                parameters={
                    "channel": "string (channel ID)",
                    "ts": "string (timestamp of message to delete)"
                }
            ),
            IntegrationAction(
                name="upload_file",
                description="Upload a file to Slack",
                parameters={
                    "channels": "string (comma-separated channel IDs)",
                    "file_content": "bytes (file content)",
                    "filename": "string",
                    "title": "string (optional)",
                    "initial_comment": "string (optional)"
                }
            ),
            IntegrationAction(
                name="create_channel",
                description="Create a new channel",
                parameters={
                    "name": "string",
                    "is_private": "boolean (optional, default false)"
                }
            ),
            IntegrationAction(
                name="archive_channel",
                description="Archive a channel",
                parameters={
                    "channel_id": "string (channel ID)"
                }
            ),
            IntegrationAction(
                name="invite_user_to_channel",
                description="Invite a user to a channel",
                parameters={
                    "channel_id": "string (channel ID)",
                    "user_id": "string (user ID)"
                }
            )
        ]

    def execute_action(self, action_name: str, params: Dict[str, Any]) -> IntegrationTestResponse:
        """Execute a Slack action"""
        try:
            # Create SlackIntegrationManager instance for execution
            slack_manager = SlackIntegrationManager(self.integration)

            # Execute the action
            result = slack_manager.execute_action(action_name, params)

            if result.get("success"):
                return IntegrationTestResponse(
                    success=True,
                    message=f"Action '{action_name}' completed successfully",
                    output=result.get("output")
                )
            else:
                return IntegrationTestResponse(
                    success=False,
                    message=f"Action '{action_name}' failed: {result.get('message')}",
                    error=result.get("error")
                )

        except Exception as e:
            return IntegrationTestResponse(
                success=False,
                message=f"Action '{action_name}' execution failed: {str(e)}",
                error=str(e)
            )

    def _update_integration_status(self, success: bool):
        """Update integration status based on connection test"""
        if success:
            self.integration.status = IntegrationStatusEnum.connected
        else:
            self.integration.status = IntegrationStatusEnum.error

        # Update last_sync timestamp
        self.integration.last_sync = datetime.utcnow()