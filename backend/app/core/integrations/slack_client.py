import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import requests
from requests.auth import HTTPBasicAuth
from pydantic import BaseModel, Field
from urllib.parse import urlencode, quote
from app.core.config import settings
from app.schemas.integrations import Integration, IntegrationStatusEnum

logger = logging.getLogger(__name__)


class SlackClient:
    """Slack API client for interacting with Slack Web API"""

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = "https://slack.com/api/"

    def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None,
                 data: Optional[Dict[str, Any]] = None, files: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to Slack API"""
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                files=files,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()

            if not result.get("ok"):
                error_message = result.get("error", "Unknown error")
                logger.error(f"Slack API error: {error_message}")
                raise Exception(f"Slack API error: {error_message}")

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Slack API request failed: {str(e)}")
            raise Exception(f"Slack API request failed: {str(e)}")

    def test_connection(self) -> Dict[str, Any]:
        """Test the Slack connection"""
        return self._request("GET", "auth.test")

    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user information"""
        return self._request("GET", "users.info", params={"user": user_id})

    def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Get channel information"""
        return self._request("GET", "conversations.info", params={"channel": channel_id})

    def list_channels(self, types: str = "public_channel,private_channel") -> Dict[str, Any]:
        """List channels"""
        return self._request("GET", "conversations.list", params={"types": types})

    def post_message(self, channel: str, text: str,
                     thread_ts: Optional[str] = None, blocks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Post a message to a channel"""
        data = {
            "channel": channel,
            "text": text,
            "thread_ts": thread_ts,
            "blocks": blocks
        }

        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        return self._request("POST", "chat.postMessage", data=data)

    def update_message(self, channel: str, ts: str, text: str, blocks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Update a message"""
        data = {
            "channel": channel,
            "ts": ts,
            "text": text,
            "blocks": blocks
        }

        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        return self._request("POST", "chat.update", data=data)

    def delete_message(self, channel: str, ts: str) -> Dict[str, Any]:
        """Delete a message"""
        return self._request("POST", "chat.delete", data={"channel": channel, "ts": ts})

    def upload_file(self, channels: str, file_content: bytes, filename: str,
                   title: Optional[str] = None, initial_comment: Optional[str] = None) -> Dict[str, Any]:
        """Upload a file"""
        files = {
            "file": (filename, file_content, "application/octet-stream")
        }

        data = {
            "channels": channels,
            "filename": filename
        }

        if title:
            data["title"] = title
        if initial_comment:
            data["initial_comment"] = initial_comment

        return self._request("POST", "files.upload", data=data, files=files)

    def create_channel(self, name: str, is_private: bool = False) -> Dict[str, Any]:
        """Create a new channel"""
        return self._request("POST", "conversations.create",
                           data={"name": name, "is_private": is_private})

    def archive_channel(self, channel_id: str) -> Dict[str, Any]:
        """Archive a channel"""
        return self._request("POST", "conversations.archive", data={"channel": channel_id})

    def invite_user_to_channel(self, channel_id: str, user_id: str) -> Dict[str, Any]:
        """Invite a user to a channel"""
        return self._request("POST", "conversations.invite",
                           data={"channel": channel_id, "users": user_id})

    def set_channel_topic(self, channel_id: str, topic: str) -> Dict[str, Any]:
        """Set channel topic"""
        return self._request("POST", "conversations.setTopic",
                           data={"channel": channel_id, "topic": topic})

    def set_channel_purpose(self, channel_id: str, purpose: str) -> Dict[str, Any]:
        """Set channel purpose"""
        return self._request("POST", "conversations.setPurpose",
                           data={"channel": channel_id, "purpose": purpose})


class SlackIntegrationManager:
    """Manager for Slack integration operations"""

    def __init__(self, integration: Integration):
        self.integration = integration
        self.client = SlackClient(self._get_bot_token())

    def _get_bot_token(self) -> str:
        """Get the bot token from integration config"""
        return self.integration.config.get("bot_token", "")

    def test_connection(self) -> Dict[str, Any]:
        """Test the Slack connection"""
        try:
            result = self.client.test_connection()
            return {
                "success": True,
                "message": "Slack connection successful",
                "output": result
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Slack connection failed: {str(e)}",
                "error": str(e)
            }

    def get_available_actions(self) -> List[Dict[str, Any]]:
        """Get available actions for Slack integration"""
        return [
            {
                "name": "post_message",
                "description": "Post a message to Slack channel",
                "parameters": {
                    "channel": "string (channel ID or name)",
                    "text": "string",
                    "thread_ts": "string (optional, for replying to threads)",
                    "blocks": "list (optional, Block Kit blocks)"
                }
            },
            {
                "name": "update_message",
                "description": "Update an existing message",
                "parameters": {
                    "channel": "string (channel ID)",
                    "ts": "string (timestamp of message to update)",
                    "text": "string",
                    "blocks": "list (optional, Block Kit blocks)"
                }
            },
            {
                "name": "delete_message",
                "description": "Delete a message",
                "parameters": {
                    "channel": "string (channel ID)",
                    "ts": "string (timestamp of message to delete)"
                }
            },
            {
                "name": "upload_file",
                "description": "Upload a file to Slack",
                "parameters": {
                    "channels": "string (comma-separated channel IDs)",
                    "file_content": "bytes (file content)",
                    "filename": "string",
                    "title": "string (optional)",
                    "initial_comment": "string (optional)"
                }
            },
            {
                "name": "create_channel",
                "description": "Create a new channel",
                "parameters": {
                    "name": "string",
                    "is_private": "boolean (optional, default false)"
                }
            },
            {
                "name": "archive_channel",
                "description": "Archive a channel",
                "parameters": {
                    "channel_id": "string (channel ID)"
                }
            },
            {
                "name": "invite_user_to_channel",
                "description": "Invite a user to a channel",
                "parameters": {
                    "channel_id": "string (channel ID)",
                    "user_id": "string (user ID)"
                }
            }
        ]

    def execute_action(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Slack action"""
        try:
            if action_name == "post_message":
                return self._execute_post_message(params)
            elif action_name == "update_message":
                return self._execute_update_message(params)
            elif action_name == "delete_message":
                return self._execute_delete_message(params)
            elif action_name == "upload_file":
                return self._execute_upload_file(params)
            elif action_name == "create_channel":
                return self._execute_create_channel(params)
            elif action_name == "archive_channel":
                return self._execute_archive_channel(params)
            elif action_name == "invite_user_to_channel":
                return self._execute_invite_user_to_channel(params)
            else:
                return {
                    "success": False,
                    "message": f"Unknown action: {action_name}",
                    "error": "Invalid action name"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Action {action_name} failed: {str(e)}",
                "error": str(e)
            }

    def _execute_post_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute post_message action"""
        channel = params.get("channel")
        text = params.get("text", "")
        thread_ts = params.get("thread_ts")
        blocks = params.get("blocks")

        if not channel:
            return {
                "success": False,
                "message": "Channel is required",
                "error": "Missing required parameter: channel"
            }

        result = self.client.post_message(channel, text, thread_ts, blocks)
        return {
            "success": True,
            "message": "Message posted successfully",
            "output": result
        }

    def _execute_update_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute update_message action"""
        channel = params.get("channel")
        ts = params.get("ts")
        text = params.get("text", "")
        blocks = params.get("blocks")

        if not channel or not ts:
            return {
                "success": False,
                "message": "Channel and timestamp are required",
                "error": "Missing required parameters"
            }

        result = self.client.update_message(channel, ts, text, blocks)
        return {
            "success": True,
            "message": "Message updated successfully",
            "output": result
        }

    def _execute_delete_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute delete_message action"""
        channel = params.get("channel")
        ts = params.get("ts")

        if not channel or not ts:
            return {
                "success": False,
                "message": "Channel and timestamp are required",
                "error": "Missing required parameters"
            }

        result = self.client.delete_message(channel, ts)
        return {
            "success": True,
            "message": "Message deleted successfully",
            "output": result
        }

    def _execute_upload_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute upload_file action"""
        channels = params.get("channels")
        file_content = params.get("file_content")
        filename = params.get("filename")
        title = params.get("title")
        initial_comment = params.get("initial_comment")

        if not channels or not file_content or not filename:
            return {
                "success": False,
                "message": "Channels, file_content, and filename are required",
                "error": "Missing required parameters"
            }

        result = self.client.upload_file(channels, file_content, filename, title, initial_comment)
        return {
            "success": True,
            "message": "File uploaded successfully",
            "output": result
        }

    def _execute_create_channel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute create_channel action"""
        name = params.get("name")
        is_private = params.get("is_private", False)

        if not name:
            return {
                "success": False,
                "message": "Channel name is required",
                "error": "Missing required parameter: name"
            }

        result = self.client.create_channel(name, is_private)
        return {
            "success": True,
            "message": "Channel created successfully",
            "output": result
        }

    def _execute_archive_channel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute archive_channel action"""
        channel_id = params.get("channel_id")

        if not channel_id:
            return {
                "success": False,
                "message": "Channel ID is required",
                "error": "Missing required parameter: channel_id"
            }

        result = self.client.archive_channel(channel_id)
        return {
            "success": True,
            "message": "Channel archived successfully",
            "output": result
        }

    def _execute_invite_user_to_channel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute invite_user_to_channel action"""
        channel_id = params.get("channel_id")
        user_id = params.get("user_id")

        if not channel_id or not user_id:
            return {
                "success": False,
                "message": "Channel ID and user ID are required",
                "error": "Missing required parameters"
            }

        result = self.client.invite_user_to_channel(channel_id, user_id)
        return {
            "success": True,
            "message": "User invited to channel successfully",
            "output": result
        }