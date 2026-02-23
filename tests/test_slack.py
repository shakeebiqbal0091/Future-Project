from app.core.integrations.slack_client import SlackClient
import logging

logger = logging.getLogger(__name__)


def test_slack_client():
    """Test the Slack client functionality"""
    print("Testing Slack Client...")

    # Create a Slack client (using a test token)
    # Note: Replace with a valid Slack bot token for real testing
    bot_token = "xoxb-test-token"  # Replace with actual token for real testing
    client = SlackClient(bot_token)

    try:
        print("1. Testing connection...")
        result = client.test_connection()
        print(f"Connection test result: {result}")

        print("\n2. Listing channels...")
        channels = client.list_channels()
        print(f"Channels: {channels.get('channels', [])}")

        print("\n3. Posting a test message...")
        message_result = client.post_message(
            channel="general",
            text="This is a test message from the AI Agent Orchestration Platform!"
        )
        print(f"Message posted: {message_result}")

        print("\n4. Uploading a test file...")
        test_content = b"This is a test file content."
        file_result = client.upload_file(
            channels="general",
            file_content=test_content,
            filename="test_file.txt",
            title="Test File"
        )
        print(f"File uploaded: {file_result}")

        print("\nSlack Client tests completed successfully!")

    except Exception as e:
        logger.error(f"Slack client test failed: {str(e)}")
        print(f"Slack client test failed: {str(e)}")


if __name__ == "__main__":
    test_slack_client()