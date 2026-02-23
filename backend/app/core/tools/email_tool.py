"""
Email Tool Implementation for Agent Executor.
Provides email sending capabilities for agents.
"""

import re
import smtplib
import ssl
from typing import Dict, Any, Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formataddr

from pydantic import BaseModel, Field, validator
from pydantic.color import Color

from app.core.tools import ToolInterface, ToolSchema, ToolParameter


class EmailPriority(str, Enum):
    """Email priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class EmailFormat(str, Enum):
    """Email format options."""
    PLAIN = "plain"
    HTML = "html"


class EmailRecipient(BaseModel):
    """Email recipient information."""

    email: str = Field(..., description="Recipient email address")
    name: Optional[str] = Field(None, description="Recipient name")
    type: str = Field(default="to", description="Recipient type (to, cc, bcc)")

    @validator("email")
    def validate_email(cls, v):
        """Validate email format."""
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, v):
            raise ValueError("Invalid email format")
        return v


class EmailInput(BaseModel):
    """Input schema for email tool."""

    to: Union[str, List[str], List[EmailRecipient]] = Field(
        ...,
        description="Recipient email address(es)"
    )
    subject: str = Field(
        ...,
        description="Email subject",
        max_length=998
    )
    body: str = Field(
        ...,
        description="Email body content",
        max_length=100000
    )
    from_email: Optional[str] = Field(
        None,
        description="Sender email address"
    )
    from_name: Optional[str] = Field(
        None,
        description="Sender name"
    )
    cc: Optional[Union[str, List[str], List[EmailRecipient]]] = Field(
        None,
        description="CC recipient email address(es)"
    )
    bcc: Optional[Union[str, List[str], List[EmailRecipient]]] = Field(
        None,
        description="BCC recipient email address(es)"
    )
    reply_to: Optional[str] = Field(
        None,
        description="Reply-to email address"
    )
    priority: EmailPriority = Field(
        EmailPriority.NORMAL,
        description="Email priority"
    )
    format: EmailFormat = Field(
        EmailFormat.PLAIN,
        description="Email format (plain text or HTML)"
    )
    attachments: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="File attachments"
    )
    custom_headers: Optional[Dict[str, str]] = Field(
        None,
        description="Custom email headers"
    )
    track_opens: bool = Field(
        default=False,
        description="Whether to track email opens"
    )
    track_clicks: bool = Field(
        default=False,
        description="Whether to track link clicks"
    )

    @validator("to", "cc", "bcc")
    def validate_recipients(cls, v):
        """Validate recipient lists."""
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return v
        raise ValueError("Recipients must be string or list")


class EmailTool(ToolInterface):
    """Email tool for sending emails."""

    def __init__(self):
        super().__init__(
            name="email",
            description="Sends emails through configured SMTP server with comprehensive validation",
            parameters=self._get_parameters()
        )
        self.smtp_config = self._get_smtp_config()

    def _get_parameters(self) -> Dict[str, ToolParameter]:
        """Get tool parameters."""
        return {
            "to": ToolParameter(
                name="to",
                type="array",
                description="Recipient email address(es)",
                required=True,
                items=ToolParameter(
                    type="string",
                    description="Email address"
                )
            ),
            "subject": ToolParameter(
                name="subject",
                type="string",
                description="Email subject",
                required=True,
                max_length=998
            ),
            "body": ToolParameter(
                name="body",
                type="string",
                description="Email body content",
                required=True,
                max_length=100000
            ),
            "from_email": ToolParameter(
                name="from_email",
                type="string",
                description="Sender email address",
                required=False,
                pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            ),
            "from_name": ToolParameter(
                name="from_name",
                type="string",
                description="Sender name",
                required=False,
                max_length=100
            ),
            "cc": ToolParameter(
                name="cc",
                type="array",
                description="CC recipient email address(es)",
                required=False
            ),
            "bcc": ToolParameter(
                name="bcc",
                type="array",
                description="BCC recipient email address(es)",
                required=False
            ),
            "reply_to": ToolParameter(
                name="reply_to",
                type="string",
                description="Reply-to email address",
                required=False,
                pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            ),
            "priority": ToolParameter(
                name="priority",
                type="string",
                description="Email priority",
                required=False,
                enum=[p.value for p in EmailPriority]
            ),
            "format": ToolParameter(
                name="format",
                type="string",
                description="Email format (plain text or HTML)",
                required=False,
                enum=[f.value for f in EmailFormat]
            ),
            "attachments": ToolParameter(
                name="attachments",
                type="array",
                description="File attachments",
                required=False
            ),
            "custom_headers": ToolParameter(
                name="custom_headers",
                type="object",
                description="Custom email headers",
                required=False
            ),
            "track_opens": ToolParameter(
                name="track_opens",
                type="boolean",
                description="Whether to track email opens",
                required=False,
                default=False
            ),
            "track_clicks": ToolParameter(
                name="track_clicks",
                type="boolean",
                description="Whether to track link clicks",
                required=False,
                default=False
            )
        }

    def _get_smtp_config(self) -> Dict[str, Any]:
        """Get SMTP configuration from environment or settings."""
        return {
            "host": "smtp.gmail.com",
            "port": 587,
            "username": "your-email@gmail.com",
            "password": "your-app-password",
            "use_tls": True,
            "timeout": 30
        }

    def _validate_input(self, arguments: Dict[str, Any]) -> EmailInput:
        """Validate and parse input arguments."""
        try:
            input_data = EmailInput(**arguments)
            return input_data
        except Exception as e:
            raise ValueError(f"Invalid email input: {str(e)}")

    def _format_email_address(self, email: str, name: Optional[str] = None) -> str:
        """Format email address with optional name."""
        if name:
            return formataddr((name, email))
        return email

    def _create_mime_message(self, input_data: EmailInput) -> MIMEMultipart:
        """Create MIME email message."""
        # Create message
        msg = MIMEMultipart()
        msg['Subject'] = input_data.subject
        msg['From'] = self._format_email_address(
            input_data.from_email or self.smtp_config["username"],
            input_data.from_name
        )

        # Set recipients
        to_addresses = []
        if isinstance(input_data.to, list):
            for recipient in input_data.to:
                if isinstance(recipient, str):
                    to_addresses.append(recipient)
                elif isinstance(recipient, dict):
                    to_addresses.append(recipient.get("email"))
        else:
            to_addresses.append(input_data.to)

        msg['To'] = ", ".join(to_addresses)

        # Set CC and BCC
        if input_data.cc:
            cc_addresses = []
            if isinstance(input_data.cc, list):
                for recipient in input_data.cc:
                    if isinstance(recipient, str):
                        cc_addresses.append(recipient)
                    elif isinstance(recipient, dict):
                        cc_addresses.append(recipient.get("email"))
            else:
                cc_addresses.append(input_data.cc)
            msg['Cc'] = ", ".join(cc_addresses)

        if input_data.bcc:
            bcc_addresses = []
            if isinstance(input_data.bcc, list):
                for recipient in input_data.bcc:
                    if isinstance(recipient, str):
                        bcc_addresses.append(recipient)
                    elif isinstance(recipient, dict):
                        bcc_addresses.append(recipient.get("email"))
            else:
                bcc_addresses.append(input_data.bcc)

        # Set reply-to
        if input_data.reply_to:
            msg.add_header('Reply-To', input_data.reply_to)

        # Set priority
        priority_mapping = {
            EmailPriority.LOW: "5",
            EmailPriority.NORMAL: "3",
            EmailPriority.HIGH: "1"
        }
        msg['X-Priority'] = priority_mapping.get(input_data.priority, "3")

        # Set custom headers
        if input_data.custom_headers:
            for header, value in input_data.custom_headers.items():
                msg[header] = value

        # Add body
        if input_data.format == EmailFormat.HTML:
            msg.attach(MIMEText(input_data.body, "html"))
        else:
            msg.attach(MIMEText(input_data.body, "plain"))

        # Add attachments
        if input_data.attachments:
            for attachment in input_data.attachments:
                try:
                    if "content" in attachment and "filename" in attachment:
                        mime_part = MIMEApplication(
                            attachment["content"],
                            Name=attachment["filename"]
                        )
                        mime_part["Content-Disposition"] = f'attachment; filename="{attachment["filename"]}"'
                        msg.attach(mime_part)
                except Exception as e:
                    logger.warning(f"Failed to add attachment: {str(e)}")

        return msg

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Send email.

        Args:
            arguments: Dictionary containing email parameters

        Returns:
            Dictionary with email sending result

        Raises:
            Exception: If email sending fails
        """
        start_time = time.time()

        # Validate input
        input_data = self._validate_input(arguments)

        # Create MIME message
        try:
            msg = self._create_mime_message(input_data)
        except Exception as e:
            raise ValueError(f"Failed to create email message: {str(e)}")

        # Connect to SMTP server
        try:
            if self.smtp_config["use_tls"]:
                server = smtplib.SMTP(self.smtp_config["host"], self.smtp_config["port"])
                server.starttls(context=ssl.create_default_context())
            else:
                server = smtplib.SMTP_SSL(self.smtp_config["host"], self.smtp_config["port"])

            server.login(self.smtp_config["username"], self.smtp_config["password"])

            # Send email
            to_addresses = []
            if isinstance(input_data.to, list):
                for recipient in input_data.to:
                    if isinstance(recipient, str):
                        to_addresses.append(recipient)
                    elif isinstance(recipient, dict):
                        to_addresses.append(recipient.get("email"))
            else:
                to_addresses.append(input_data.to)

            if input_data.cc:
                if isinstance(input_data.cc, list):
                    for recipient in input_data.cc:
                        if isinstance(recipient, str):
                            to_addresses.append(recipient)
                        elif isinstance(recipient, dict):
                            to_addresses.append(recipient.get("email"))
                else:
                    to_addresses.append(input_data.cc)

            server.sendmail(
                input_data.from_email or self.smtp_config["username"],
                to_addresses,
                msg.as_string()
            )

            server.quit()

            return {
                "success": True,
                "message": "Email sent successfully",
                "to": to_addresses,
                "subject": input_data.subject,
                "timestamp": str(datetime.utcnow()),
                "duration_ms": int((time.time() - start_time) * 1000)
            }

        except smtplib.SMTPException as e:
            return {
                "success": False,
                "error": f"SMTP error: {str(e)}",
                "timestamp": str(datetime.utcnow()),
                "duration_ms": int((time.time() - start_time) * 1000)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": str(datetime.utcnow()),
                "duration_ms": int((time.time() - start_time) * 1000)
            }