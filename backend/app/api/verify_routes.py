import sys
import os
import json
from pathlib import Path

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Verifying API Routes Setup...")
print("=" * 50)

# Check if main files exist
required_files = [
    "C:\\Users\\Binary Marvels\\Music\\Future Project\\backend\\app\\api\\routes\\agents.py",
    "C:\\Users\\Binary Marvels\\Music\\Future Project\\backend\\app\\schemas\\agents.py",
    "C:\\Users\\Binary Marvels\\Music\\Future Project\\backend\\app\\api\\docs\\agents.md",
    "C:\\Users\\Binary Marvels\\Music\\Future Project\\backend\\app\\api\\README.md",
    "C:\\Users\\Binary Marvels\\Music\\Future Project\\backend\\app\\api\\verify_setup.py",
    "C:\\Users\\Binary Marvels\\Music\\Future Project\\backend\\app\\api\\conftest.py",
    "C:\\Users\\Binary Marvels\\Music\\Future Project\\backend\\app\\api\\test_agents.py"
]

print("\nChecking required files...")
print("-" * 30)

all_files_exist = True
for file_path in required_files:
    if Path(file_path).exists():
        print(f"✓ {file_path}")
    else:
        print(f"✗ Missing: {file_path}")
        all_files_exist = False

print(f"\n{'=' * 50}")
if all_files_exist:
    print("✅ All required files exist!")
else:
    print("❌ Some files are missing!")

print("\nValidating route definitions...")
print("-" * 30)

try:
    # Test basic imports
    from app.api.routes import agents_router
    from app.schemas.agents import AgentCreate, Agent
    from app.models.models import Agent

    print("✓ Basic imports successful")

    # Check if agents_router has the required routes
    required_routes = [
        "POST /agents",
        "GET /agents",
        "GET /agents/{agent_id}",
        "PUT /agents/{agent_id}",
        "DELETE /agents/{agent_id}",
        "POST /agents/{agent_id}/test",
        "GET /agents/{agent_id}/versions",
        "POST /agents/{agent_id}/deploy",
        "GET /agents/{agent_id}/metrics"
    ]

    print(f"\nChecking route definitions...")
    for route in required_routes:
        if route in str(agents_router):
            print(f"  ✓ {route}")
        else:
            print(f"  ✗ {route} - NOT FOUND")
            all_files_exist = False

    print(f"\n{'=' * 50}")
    if all_files_exist:
        print("🎉 API Routes Setup Complete!")
        print("📊 All 9 agent routes have been successfully created!")
        print("🔧 Files are properly structured and ready for testing")
        print("📚 Documentation is available in api/docs/agents.md")
    else:
        print("⚠️  Some issues found - please check the missing components")

except Exception as e:
    print(f"❌ Error during verification: {e}")
    sys.exit(1)

print(f"\n{'=' * 50}")
print("🚀 Next Steps:")
print("1. Run tests: pytest api/test_agents.py")
print("2. Start the API server")
print("3. Test endpoints using Swagger UI")
print("4. Integrate with frontend")
print(f"{'=' * 50}")