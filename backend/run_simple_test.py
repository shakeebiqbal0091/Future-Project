import sys
sys.path.append('.')
import os

# Add the app directory to the path
app_path = os.path.join(os.path.dirname(__file__), 'app')
sys.path.append(app_path)

print('Current working directory:', os.getcwd())
print('Python path:', sys.path)

# Try to import the test module
try:
    from api.simple_test_organizations import TestOrganizationsRoutes
    print('Import successful!')

    # Run the tests
    import pytest
    pytest.main(['-v'])

except Exception as e:
    print('Import failed:', e)
    print('Traceback:')
    import traceback
    traceback.print_exc()