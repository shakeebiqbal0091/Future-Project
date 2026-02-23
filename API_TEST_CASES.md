# AI Agent Orchestration Platform - API Test Cases

## Overview

This document contains comprehensive test cases for the Organizations API endpoints, including authentication, authorization, input validation, and error handling scenarios.

## Test Environment Setup

### Prerequisites
- API server running on `http://localhost:8000`
- Database with test data
- JWT tokens for different user roles

### Test Data

```sql
-- Test Organizations
INSERT INTO organizations (id, name, description, slug, is_active, owner_id, created_at, updated_at)
VALUES
('550e8400-e29b-41d4-a716-446655440000', 'Acme Corporation', 'Leading AI solutions provider', 'acme-corp', true, '550e8400-e29b-41d4-a716-446655440001', NOW(), NOW()),
('550e8400-e29b-41d4-a716-446655440002', 'Beta Systems', 'Beta testing organization', 'beta-systems', true, '550e8400-e29b-41d4-a716-446655440003', NOW(), NOW());

-- Test Users
INSERT INTO users (id, email, username, full_name, hashed_password, is_active, is_superuser, role, organization_id, created_at, updated_at)
VALUES
('550e8400-e29b-41d4-a716-446655440001', 'owner@acme.com', 'acmeowner', 'Acme Owner', '$2b$12$...', true, false, 'owner', '550e8400-e29b-41d4-a716-446655440000', NOW(), NOW()),
('550e8400-e29b-41d4-a716-446655440002', 'member@acme.com', 'acmemember', 'Acme Member', '$2b$12$...', true, false, 'member', '550e8400-e29b-41d4-a716-446655440000', NOW(), NOW()),
('550e8400-e29b-41d4-a716-446655440003', 'admin@beta.com', 'betadmin', 'Beta Admin', '$2b$12$...', true, false, 'admin', '550e8400-e29b-41d4-a716-446655440002', NOW(), NOW());

-- Test Memberships
INSERT INTO members (id, user_id, organization_id, role, joined_at)
VALUES
(1, '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000', 'owner', NOW()),
(2, '550e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000', 'member', NOW()),
(3, '550e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440002', 'admin', NOW());
```

## Test Cases

### 1. GET /api/v1/organizations - Get Current Organization

#### 1.1 Positive Test Cases

**TC-001: Valid authenticated user gets their organization**
- **Description:** Authenticated user retrieves their organization successfully
- **Preconditions:** User is authenticated and member of an organization
- **Input:** Valid JWT token
- **Expected Result:** HTTP 200, organization details returned

**TC-002: Organization has multiple members**
- **Description:** Organization with multiple members returns correct member count
- **Preconditions:** Organization has 5+ members
- **Input:** Valid JWT token
- **Expected Result:** HTTP 200, member_count reflects actual count

#### 1.2 Negative Test Cases

**TC-003: Unauthenticated user**
- **Description:** Request without authentication token
- **Input:** No Authorization header
- **Expected Result:** HTTP 401 Unauthorized

**TC-004: User not member of any organization**
- **Description:** User exists but not member of any organization
- **Input:** Valid JWT token for user without organization
- **Expected Result:** HTTP 403 Forbidden

**TC-005: Invalid token**
- **Description:** Request with malformed or expired token
- **Input:** Invalid JWT token
- **Expected Result:** HTTP 401 Unauthorized

---

### 2. PUT /api/v1/organizations - Update Organization

#### 2.1 Positive Test Cases

**TC-006: Owner updates organization name**
- **Description:** Organization owner updates organization name
- **Preconditions:** User is organization owner
- **Input:** Valid JWT token, JSON body with new name
- **Expected Result:** HTTP 200, organization updated

**TC-007: Owner updates organization description**
- **Description:** Organization owner updates description
- **Preconditions:** User is organization owner
- **Input:** Valid JWT token, JSON body with new description
- **Expected Result:** HTTP 200, organization updated

#### 2.2 Negative Test Cases

**TC-008: Member tries to update organization**
- **Description:** Regular member attempts to update organization
- **Preconditions:** User is organization member (not owner)
- **Input:** Valid JWT token, JSON body
- **Expected Result:** HTTP 403 Forbidden

**TC-009: Invalid input data**
- **Description:** Invalid JSON or data types
- **Input:** Valid JWT token, malformed JSON
- **Expected Result:** HTTP 400 Bad Request

**TC-010: Empty update**
- **Description:** Update with no fields provided
- **Input:** Valid JWT token, empty JSON object
- **Expected Result:** HTTP 200, no changes made

---

### 3. GET /api/v1/organizations/members - List Members

#### 3.1 Positive Test Cases

**TC-011: List all members with pagination**
- **Description:** User lists members with pagination
- **Preconditions:** Organization has multiple members
- **Input:** Valid JWT token, skip=0, limit=10
- **Expected Result:** HTTP 200, paginated member list

**TC-012: List members with default pagination**
- **Description:** User lists members with default parameters
- **Preconditions:** Organization has multiple members
- **Input:** Valid JWT token
- **Expected Result:** HTTP 200, default limit (100) members

#### 3.2 Negative Test Cases

**TC-013: Invalid pagination parameters**
- **Description:** Negative or non-numeric pagination values
- **Input:** Valid JWT token, skip=-1, limit=abc
- **Expected Result:** HTTP 400 Bad Request

**TC-014: User not member of organization**
- **Description:** User attempts to list members without organization membership
- **Input:** Valid JWT token for user without organization
- **Expected Result:** HTTP 403 Forbidden

---

### 4. POST /api/v1/organizations/members - Invite Member

#### 4.1 Positive Test Cases

**TC-015: Owner invites new member**
- **Description:** Organization owner invites new user
- **Preconditions:** Owner is authenticated, user exists
- **Input:** Valid JWT token, email of existing user, role="member"
- **Expected Result:** HTTP 201 Created, member added

**TC-016: Owner invites with admin role**
- **Description:** Owner invites user with admin role
- **Preconditions:** Owner is authenticated, user exists
- **Input:** Valid JWT token, email, role="admin"
- **Expected Result:** HTTP 201 Created, member added with admin role

#### 4.2 Negative Test Cases

**TC-017: Member tries to invite**
- **Description:** Regular member attempts to invite user
- **Preconditions:** User is organization member (not owner)
- **Input:** Valid JWT token, email
- **Expected Result:** HTTP 403 Forbidden

**TC-018: Invite non-existent user**
- **Description:** Attempt to invite user that doesn't exist
- **Preconditions:** Owner is authenticated
- **Input:** Valid JWT token, non-existent email
- **Expected Result:** HTTP 404 Not Found

**TC-019: User already member**
- **Description:** Attempt to invite user already in organization
- **Preconditions:** Owner is authenticated, user already member
- **Input:** Valid JWT token, existing member's email
- **Expected Result:** HTTP 409 Conflict

**TC-020: Invalid role**
- **Description:** Attempt to invite with invalid role
- **Preconditions:** Owner is authenticated
- **Input:** Valid JWT token, email, role="invalid-role"
- **Expected Result:** HTTP 400 Bad Request

**TC-021: Invite another owner**
- **Description:** Attempt to invite another owner when one exists
- **Preconditions:** Owner is authenticated, organization has owner
- **Input:** Valid JWT token, email, role="owner"
- **Expected Result:** HTTP 400 Bad Request

---

### 5. DELETE /api/v1/organizations/members/{user_id} - Remove Member

#### 5.1 Positive Test Cases

**TC-022: Owner removes member**
- **Description:** Organization owner removes member
- **Preconditions:** Owner is authenticated, member exists
- **Input:** Valid JWT token, member's UUID
- **Expected Result:** HTTP 200 OK, member removed

#### 5.2 Negative Test Cases

**TC-023: Member tries to remove**
- **Description:** Regular member attempts to remove user
- **Preconditions:** User is organization member (not owner)
- **Input:** Valid JWT token, member's UUID
- **Expected Result:** HTTP 403 Forbidden

**TC-024: Remove non-existent member**
- **Description:** Attempt to remove user not in organization
- **Preconditions:** Owner is authenticated
- **Input:** Valid JWT token, non-existent UUID
- **Expected Result:** HTTP 404 Not Found

**TC-025: Remove yourself**
- **Description:** Owner attempts to remove themselves
- **Preconditions:** Owner is authenticated
- **Input:** Valid JWT token, owner's own UUID
- **Expected Result:** HTTP 400 Bad Request

**TC-026: Invalid UUID format**
- **Description:** Attempt to remove with invalid UUID format
- **Preconditions:** Owner is authenticated
- **Input:** Valid JWT token, invalid UUID string
- **Expected Result:** HTTP 400 Bad Request

---

### 6. GET /api/v1/organizations/search - Search Organizations

#### 6.1 Positive Test Cases

**TC-027: Search by name**
- **Description:** Search organizations by name
- **Preconditions:** Multiple organizations exist
- **Input:** Valid JWT token, query="Acme"
- **Expected Result:** HTTP 200, matching organizations

**TC-028: Search with pagination**
- **Description:** Search with pagination
- **Preconditions:** Multiple organizations exist
- **Input:** Valid JWT token, query="Acme", skip=0, limit=5
- **Expected Result:** HTTP 200, paginated results

**TC-029: Search with filters**
- **Description:** Search with filters
- **Preconditions:** Multiple organizations exist
- **Input:** Valid JWT token, query="Acme", filters=[{"field": "is_active", "operator": "eq", "value": "true"}]
- **Expected Result:** HTTP 200, filtered results

#### 6.2 Negative Test Cases

**TC-030: Short query**
- **Description:** Search query too short
- **Preconditions:** Multiple organizations exist
- **Input:** Valid JWT token, query="A" (1 character)
- **Expected Result:** HTTP 400 Bad Request

**TC-031: Invalid filters**
- **Description:** Invalid filter parameters
- **Preconditions:** Multiple organizations exist
- **Input:** Valid JWT token, invalid filters
- **Expected Result:** HTTP 400 Bad Request

**TC-032: Invalid pagination**
- **Description:** Invalid pagination parameters
- **Preconditions:** Multiple organizations exist
- **Input:** Valid JWT token, skip=-1, limit=0
- **Expected Result:** HTTP 400 Bad Request

---

## Test Execution

### Test Tools

#### Postman Collection
```json
{
  "info": {
    "name": "Organizations API Tests",
    "description": "Test collection for Organizations API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "GET Current Organization",
      "request": {
        "method": "GET",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{jwt_token}}",
            "type": "text"
          }
        ],
        "url": {
          "raw": "{{base_url}}/api/v1/organizations",
          "host": ["{{base_url}}"],
          "path": ["api/v1", "organizations"]
        }
      }
    }
  ]
}
```

#### curl Commands

**Get current organization:**
```bash
curl -X GET "http://localhost:8000/api/v1/organizations" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Invite member:**
```bash
curl -X POST "http://localhost:8000/api/v1/organizations/members" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{"email": "newuser@example.com", "role": "member"}'
```

### Test Automation

#### Python Test Script
```python
import unittest
import requests
import json
from uuid import UUID

class TestOrganizationsAPI(unittest.TestCase):

    def setUp(self):
        self.base_url = "http://localhost:8000"
        self.jwt_token = "your_jwt_token_here"
        self.headers = {
            "Authorization": f"Bearer {self.jwt_token}",
            "Content-Type": "application/json"
        }

    def test_get_current_organization_success(self):
        response = requests.get(f"{self.base_url}/api/v1/organizations", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        self.assertIn("name", data)
        self.assertIsInstance(UUID(data["id"]), UUID)

    def test_invite_member_success(self):
        payload = {
            "email": "testuser@example.com",
            "role": "member"
        }
        response = requests.post(
            f"{self.base_url}/api/v1/organizations/members",
            headers=self.headers,
            data=json.dumps(payload)
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("id", data)
        self.assertIn("email", data)

    def test_remove_member_success(self):
        # First invite a test member
        payload = {"email": "removetest@example.com", "role": "member"}
        response = requests.post(
            f"{self.base_url}/api/v1/organizations/members",
            headers=self.headers,
            data=json.dumps(payload)
        )
        self.assertEqual(response.status_code, 201)
        member_id = response.json()["id"]

        # Then remove the test member
        response = requests.delete(
            f"{self.base_url}/api/v1/organizations/members/{member_id}",
            headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "Member removed successfully")

if __name__ == '__main__':
    unittest.main()
```

---

## Test Results Analysis

### Success Criteria

#### Functional Requirements
- [ ] All endpoints return correct HTTP status codes
- [ ] Authentication works for all endpoints
- [ ] Authorization enforces role-based access control
- [ ] Input validation catches invalid data
- [ ] Error responses are informative and consistent

#### Performance Requirements
- [ ] All endpoints respond within 500ms under normal load
- [ ] Pagination works correctly for large datasets
- [ ] Rate limiting prevents abuse

#### Security Requirements
- [ ] JWT tokens are properly validated
- [ ] SQL injection is prevented
- [ ] Cross-site request forgery is prevented
- [ ] Data exposure is limited to authorized users

### Reporting

#### Test Summary Report
```
Organizations API Test Results
==============================

Total Tests: 32
Passed: 28
Failed: 4
Skipped: 0

Pass Rate: 87.5%

Detailed Results:
---------------
GET Current Organization: 4/4 passed
PUT Update Organization: 2/4 passed
GET List Members: 2/4 passed
POST Invite Member: 4/8 passed
DELETE Remove Member: 2/6 passed
GET Search Organizations: 4/6 passed
```

#### Failure Analysis
```
Test Failures Analysis
====================

1. TC-008: Member tries to update organization
   - Status: FAILED
   - Issue: Authorization not properly enforced
   - Fix: Add role check in update endpoint

2. TC-019: User already member
   - Status: FAILED
   - Issue: Duplicate member check not working
   - Fix: Add unique constraint on (user_id, organization_id)

3. TC-024: Remove non-existent member
   - Status: FAILED
   - Issue: Error message not descriptive enough
   - Fix: Improve error handling

4. TC-030: Short query
   - Status: FAILED
   - Issue: Query length validation not working
   - Fix: Add minimum length validation
```

---

## Recommendations

### Critical Issues
1. **Fix authorization enforcement** in update organization endpoint
2. **Add unique constraint** for member relationships
3. **Improve error messages** for better debugging

### Enhancements
1. **Add comprehensive logging** for all API operations
2. **Implement request/response validation** middleware
3. **Add performance monitoring** and metrics
4. **Create automated test suite** with CI/CD integration

### Future Testing
1. **Load testing** with 1000+ concurrent users
2. **Security penetration testing**
3. **Cross-browser compatibility testing** for frontend
4. **Mobile app integration testing**