from app.core.integrations.slack_integration_manager import SlackIntegrationManager
from app.schemas.integrations import Integration, IntegrationStatusEnum
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def create_test_slack_integration() -> Integration:
    """Create a test Slack integration"""
    return Integration(
        id="test-slack-integration",
        organization_id="test-org",
        type="slack",
        name="Test Slack Integration",
        credentials_encrypted="encrypted-credentials",
        config={
            "bot_token": "xoxb-test-token"  # Replace with actual token for real testing
        },
        status=IntegrationStatusEnum.connected,
        last_sync=None,
        created_at=datetime.utcnow()
    )

def demonstrate_slack_integration():
    """Demonstrate Slack integration functionality"""
    print("Demonstrating Slack Integration...")

    # Create test integration
    integration = create_test_slack_integration()
    print("Created test Slack integration")

    # Create Slack integration manager
    manager = SlackIntegrationManager(integration)
    print("Created SlackIntegrationManager instance")

    try:
        # Test connection
        print("\n1. Testing Slack connection...")
        test_result = manager.test_connection()
        print(f"Connection test result: {test_result}")

        if not test_result.get("success"):
            print("Skipping remaining tests due to connection failure")
            return

        # Get available actions
        print("\n2. Getting available Slack actions...")
        actions = manager.get_available_actions()
        print("Available actions:")
        for action in actions:
            print(f"- {action.name}: {action.description}")
            print(f"  Parameters: {action.parameters}")

        # Execute post_message action
        print("\n3. Executing post_message action...")
        post_params = {
            "channel": "general",
            "text": "This is a test message from the AI Agent Orchestration Platform!"
        }
        post_result = manager.execute_action("post_message", post_params)
        print(f"post_message result: {post_result}")

        # Execute create_channel action
        print("\n4. Executing create_channel action...")
        create_params = {
            "name": "test-channel-from-ai-platform",
            "is_private": False
        }
        create_result = manager.execute_action("create_channel", create_params)
        print(f"create_channel result: {create_result}")

        # Execute upload_file action
        print("\n5. Executing upload_file action...")
        file_content = b"This is a test file uploaded via the AI Agent Orchestration Platform."
        upload_params = {
            "channels": "general",
            "file_content": file_content,
            "filename": "test_upload.txt",
            "title": "Test Upload"
        }
        upload_result = manager.execute_action("upload_file", upload_params)
        print(f"upload_file result: {upload_result}")

        print("\nSlack integration demonstration completed successfully!")

    except Exception as e:
        logger.error(f"Slack integration demonstration failed: {str(e)}")
        print(f"Slack integration demonstration failed: {str(e)}")


if __name__ == "__main__":
    demonstrate_slack_integration()