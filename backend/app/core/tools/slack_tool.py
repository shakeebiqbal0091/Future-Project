"""
Slack Tool Implementation for Agent Executor.
Provides Slack messaging capabilities for agents.
"""

import re
import time
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, validator

import httpx
from yarl import URL

from app.core.tools import ToolInterface, ToolSchema, ToolParameter


class SlackChannelType(str, Enum):
    """Slack channel types."""
    PUBLIC = "public"
    PRIVATE = "private"
    DIRECT_MESSAGE = "im"
    MULTI_DIRECT_MESSAGE = "mpim"


class SlackMessageType(str, Enum):
    """Slack message types."""
    TEXT = "text"
    BLOCK = "block"
    FILE = "file"


class SlackBlockFormat(str, Enum):
    """Slack block formatting options."""
    MARKDOWN = "mrkdwn"
    PLAIN_TEXT = "plain_text"


class SlackInput(BaseModel):
    """Input schema for Slack tool."""

    channel: str = Field(
        ...,
        description="Slack channel, user, or group ID",
        max_length=100
    )
    text: str = Field(
        ...,
        description="Message text",
        max_length=40000
    )
    thread_ts: Optional[str] = Field(
        None,
        description="Timestamp of parent message to reply to"
    )
    blocks: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Array of blocks for rich message formatting"
    )
    attachments: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Array of attachments"
    )
    icon_emoji: Optional[str] = Field(
        None,
        description="Emoji to use as the icon for this message"
    )
    icon_url: Optional[str] = Field(
        None,
        description="URL to an image to use as the icon for this message"
    )
    username: Optional[str] = Field(
        None,
        description="Name of bot to use as the user name for this message"
    )
    as_user: bool = Field(
        default=False,
        description="Pass true to post the message as the authed user"
    )
    link_names: bool = Field(
        default=True,
        description="Find and link channel names and usernames"
    )
    parse: str = Field(
        default="full",
        description="Change how messages are treated"
    )
    unfurl_links: bool = Field(
        default=True,
        description="Unfurl links to primarily text-based content"
    )
    unfurl_media: bool = Field(
        default=True,
        description="Unfurl media content"
    )
    mrkdwn: bool = Field(
        default=True,
        description="Disable Slack markup parsing"
    )

    @validator("channel")
    def validate_channel(cls, v):
        """Validate channel format."""
        if not v:
            raise ValueError("Channel ID is required")
        if len(v) > 100:
            raise ValueError("Channel ID is too long")
        # Channel IDs start with C, G, D, or specific prefixes
        if not re.match(r'^[CGDU]\w+$', v) and not v.startswith('!') and not v.startswith('@'):
            raise ValueError("Invalid channel ID format")
        return v


class SlackTool(ToolInterface):
    """Slack tool for posting messages."""

    def __init__(self):
        super().__init__(
            name="slack",
            description="Posts messages to Slack channels, users, or groups with comprehensive formatting options",
            parameters=self._get_parameters()
        )
        self.slack_config = self._get_slack_config()

    def _get_parameters(self) -> Dict[str, ToolParameter]:
        """Get tool parameters."""
        return {
            "channel": ToolParameter(
                name="channel",
                type="string",
                description="Slack channel, user, or group ID",
                required=True,
                max_length=100,
                pattern=r"^[CGDU]\w+$|^![a-zA-Z]+|^@[a-zA-Z0-9._-]+$"
            ),
            "text": ToolParameter(
                name="text",
                type="string",
                description="Message text",
                required=True,
                max_length=40000
            ),
            "thread_ts": ToolParameter(
                name="thread_ts",
                type="string",
                description="Timestamp of parent message to reply to",
                required=False,
                pattern=r'\d+\.\d+'
            ),
            "blocks": ToolParameter(
                name="blocks",
                type="array",
                description="Array of blocks for rich message formatting",
                required=False
            ),
            "attachments": ToolParameter(
                name="attachments",
                type="array",
                description="Array of attachments",
                required=False
            ),
            "icon_emoji": ToolParameter(
                name="icon_emoji",
                type="string",
                description="Emoji to use as the icon for this message",
                required=False,
                pattern=r'^:[\w+-]+:$'
            ),
            "icon_url": ToolParameter(
                name="icon_url",
                type="string",
                description="URL to an image to use as the icon for this message",
                required=False,
                pattern=r'^https?://.+'
            ),
            "username": ToolParameter(
                name="username",
                type="string",
                description="Name of bot to use as the user name for this message",
                required=False,
                max_length=100
            ),
            "as_user": ToolParameter(
                name="as_user",
                type="boolean",
                description="Pass true to post the message as the authed user",
                required=False,
                default=False
            ),
            "link_names": ToolParameter(
                name="link_names",
                type="boolean",
                description="Find and link channel names and usernames",
                required=False,
                default=True
            ),
            "parse": ToolParameter(
                name="parse",
                type="string",
                description="Change how messages are treated",
                required=False,
                enum=["none", "full"]
            ),
            "unfurl_links": ToolParameter(
                name="unfurl_links",
                type="boolean",
                description="Unfurl links to primarily text-based content",
                required=False,
                default=True
            ),
            "unfurl_media": ToolParameter(
                name="unfurl_media",
                type="boolean",
                description="Unfurl media content",
                required=False,
                default=True
            ),
            "mrkdwn": ToolParameter(
                name="mrkdwn",
                type="boolean",
                description="Disable Slack markup parsing",
                required=False,
                default=True
            )
        }

    def _get_slack_config(self) -> Dict[str, Any]:
        """Get Slack configuration from environment or settings."""
        return {
            "bot_token": "xoxb-your-slack-bot-token",
            "api_url": "https://slack.com/api/chat.postMessage",
            "timeout": 30
        }

    def _validate_input(self, arguments: Dict[str, Any]) -> SlackInput:
        """Validate and parse input arguments."""
        try:
            input_data = SlackInput(**arguments)
            return input_data
        except Exception as e:
            raise ValueError(f"Invalid Slack input: {str(e)}")

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Post message to Slack.

        Args:
            arguments: Dictionary containing Slack message parameters

        Returns:
            Dictionary with Slack posting result

        Raises:
            Exception: If posting fails
        """
        start_time = time.time()

        # Validate input
        input_data = self._validate_input(arguments)

        # Prepare request data
        request_data = {
            "channel": input_data.channel,
            "text": input_data.text,
            "link_names": input_data.link_names,
            "parse": input_data.parse,
            "unfurl_links": input_data.unfurl_links,
            "unfurl_media": input_data.unfurl_media,
            "mrkdwn": input_data.mrkdwn
        }

        # Add optional parameters
        if input_data.thread_ts:
            request_data["thread_ts"] = input_data.thread_ts

        if input_data.blocks:
            request_data["blocks"] = input_data.blocks

        if input_data.attachments:
            request_data["attachments"] = input_data.attachments

        if input_data.icon_emoji:
            request_data["icon_emoji"] = input_data.icon_emoji

        if input_data.icon_url:
            request_data["icon_url"] = input_data.icon_url

        if input_data.username:
            request_data["username"] = input_data.username

        if input_data.as_user:
            request_data["as_user"] = input_data.as_user

        # Prepare headers
        headers = {
            "Authorization": f"Bearer {self.slack_config['bot_token']}",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "AgentFlow-Slack/1.0",
            "X-Slack-Request-Timestamp": str(int(time.time()))
        }

        try:
            async with httpx.AsyncClient(timeout=self.slack_config["timeout"]) as client:
                response = await client.post(
                    self.slack_config["api_url"],
                    headers=headers,
                    json=request_data
                )

                response_data = response.json()

                if response.status_code == 200 and response_data.get("ok"):
                    return {
                        "success": True,
                        "message": "Message posted to Slack",
                        "channel": response_data.get("channel"),
                        "ts": response_data.get("ts"),
                        "response": response_data,
                        "duration_ms": int((time.time() - start_time) * 1000)
                    }
                else:
                    return {
                        "success": False,
                        "error": response_data.get("error", "Unknown Slack API error"),
                        "response": response_data,
                        "status_code": response.status_code,
                        "duration_ms": int((time.time() - start_time) * 1000)
                    }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Slack API request timeout",
                "duration_ms": int((time.time() - start_time) * 1000)
            }

        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"Slack API error: {e.response.status_code} {e.response.text}",
                "status_code": e.response.status_code,
                "duration_ms": int((time.time() - start_time) * 1000)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration_ms": int((time.time() - start_time) * 1000)
            }