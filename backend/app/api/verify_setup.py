import sys
import os

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test imports
print("Testing API routes imports...")

try:
    from app.api.routes import agents_router
    print("✓ agents_router imported successfully")
except ImportError as e:
    print(f"✗ Failed to import agents_router: {e}")


print("\nTesting schemas imports...")

try:
    from app.schemas.agents import AgentCreate, Agent
    print("✓ AgentCreate and Agent schemas imported successfully")
except ImportError as e:
    print(f"✗ Failed to import agents schemas: {e}")


print("\nTesting models...")

try:
    from app.models.models import Agent
    print("✓ Agent model imported successfully")
except ImportError as e:
    print(f"✗ Failed to import Agent model: {e}")


print("\nTesting database connection...")

try:
    from app.core.database import engine
    print("✓ Database engine imported successfully")
except ImportError as e:
    print(f"✗ Failed to import database engine: {e}")


print("\nTesting security utilities...")

try:
    from app.core.security.utils import RateLimiter
    print("✓ RateLimiter imported successfully")
except ImportError as e:
    print(f"✗ Failed to import RateLimiter: {e}")


print("\nTesting authentication...")

try:
    from app.core.security.auth_handler import AuthHandler
    print("✓ AuthHandler imported successfully")
except ImportError as e:
    print(f"✗ Failed to import AuthHandler: {e}")


print("\nTesting all imports completed!")

# Test if all required files exist
required_files = [
    "C:\\Users\\Binary Marvels\\Music\\Future Project\\backend\\app\\api\\routes\\agents.py",
    "C:\\Users\\Binary Marvels\\Music\\Future Project\\backend\\app\\schemas\\agents.py",
    "C:\\Users\\Binary Marvels\\Music\\Future Project\\backend\\app\\api\\docs\\agents.md"
]

print("\nChecking required files...")

for file_path in required_files:
    if os.path.exists(file_path):
        print(f"✓ {file_path}")
    else:
        print(f"✗ Missing: {file_path}")

print("\nAPI Routes Setup Complete!")