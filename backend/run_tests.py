import sys
sys.path.append('.')
import os

# Add the app directory to the path
app_path = os.path.join(os.path.dirname(__file__), 'app')
sys.path.append(app_path)

print('Current working directory:', os.getcwd())
print('Python path:', sys.path)

# Try to run the tests
import pytest
pytest.main(["api/test_organizations_final.py", "-v"])
