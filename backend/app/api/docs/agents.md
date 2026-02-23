# API Routes - Agents Management

This document describes the API routes for agent management in the AI Agent Orchestration Platform.

## Base URL
```
/api/v1/agents
```

## Routes

### 1. POST /api/v1/agents - Create a new agent

Creates a new agent with the specified configuration.

**Request Body:**
```json
{
  "name": "string",
  "role": "string",
  "instructions": "string",
  "model": "claude|gpt4|gpt3_5|gemini",
  "tools": ["calculator", "web_search", "http_request", "database_query", "email_send", "slack_post"],
  "config": {}
}
```

**Response:**
```json
{
  "agent": {
    "id": "uuid",
    "organization_id": "uuid",
    "name": "string",
    "role": "string",
    "instructions": "string",
    "model": "string",
    "tools": ["string"],
    "config": {},
    "status": "active|inactive|archived",
    "version": 1,
    "created_by": "uuid",
    "created_at": "datetime",
    "updated_at": "datetime"
  },
  "message": "Agent created successfully"
}
```

**Rate Limits:** 10 requests per hour per user

---

### 2. GET /api/v1/agents - List agents with pagination

Lists all agents with pagination support.

**Query Parameters:**
- `page` (int, optional): Page number (default: 1)
- `size` (int, optional): Page size (default: 10)

**Response:**
```json
{
  "agents": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "name": "string",
      "role": "string",
      "instructions": "string",
      "model": "string",
      "tools": ["string"],
      "config": {},
      "status": "active|inactive|archived",
      "version": 1,
      "created_by": "uuid",
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ],
  "total": 100,
  "page": 1,
  "size": 10
}
```

---

### 3. GET /api/v1/agents/{id} - Get agent details

Gets detailed information about a specific agent.

**Response:**
```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "name": "string",
  "role": "string",
  "instructions": "string",
  "model": "string",
  "tools": ["string"],
  "config": {},
  "status": "active|inactive|archived",
  "version": 1,
  "created_by": "uuid",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

**Error Responses:**
- 404 Not Found: Agent with specified ID not found

---

### 4. PUT /api/v1/agents/{id} - Update agent

Updates an existing agent with new configuration.

**Request Body:**
```json
{
  "name": "string",
  "role": "string",
  "instructions": "string",
  "model": "claude|gpt4|gpt3_5|gemini",
  "tools": ["calculator", "web_search", "http_request", "database_query", "email_send", "slack_post"],
  "config": {},
  "status": "active|inactive|archived"
}
```

**Response:**
```json
{
  "agent": {
    "id": "uuid",
    "organization_id": "uuid",
    "name": "string",
    "role": "string",
    "instructions": "string",
    "model": "string",
    "tools": ["string"],
    "config": {},
    "status": "active|inactive|archived",
    "version": 1,
    "created_by": "uuid",
    "created_at": "datetime",
    "updated_at": "datetime"
  },
  "message": "Agent updated successfully"
}
```

**Rate Limits:** 20 requests per hour per user

---

### 5. DELETE /api/v1/agents/{id} - Delete agent

Deletes an agent permanently.

**Response:**
```json
{
  "message": "Agent deleted successfully"
}
```

**Error Responses:**
- 404 Not Found: Agent with specified ID not found

**Rate Limits:** 20 requests per hour per user

---

### 6. POST /api/v1/agents/{id}/test - Test agent with sample input

Tests an agent with sample input to verify its functionality.

**Request Body:**
```json
{
  "input": {}
}
```

**Response:**
```json
{
  "success": true,
  "message": "Agent test completed successfully",
  "output": {
    "input_received": {},
    "agent_response": "string",
    "confidence": 0.95
  },
  "error": "string (optional)"
}
```

**Rate Limits:** 50 requests per hour per user

---

### 7. GET /api/v1/agents/{id}/versions - List agent versions

Lists all versions of a specific agent.

**Query Parameters:**
- `page` (int, optional): Page number (default: 1)
- `size` (int, optional): Page size (default: 10)

**Response:**
```json
{
  "versions": [
    {
      "id": "uuid",
      "agent_id": "uuid",
      "version": 1,
      "config": {},
      "deployed_at": "datetime",
      "deployed_by": "uuid"
    }
  ],
  "total": 5,
  "page": 1,
  "size": 10
}
```

---

### 8. POST /api/v1/agents/{id}/deploy - Deploy a specific version

Deploys a specific version of an agent.

**Request Body:**
```json
{
  "version_number": 1
}
```

**Response:**
```json
{
  "version": {
    "id": "uuid",
    "agent_id": "uuid",
    "version": 1,
    "config": {},
    "deployed_at": "datetime",
    "deployed_by": "uuid"
  },
  "message": "Agent version deployed successfully"
}
```

**Error Responses:**
- 404 Not Found: Agent or version not found

**Rate Limits:** 20 requests per hour per user

---

### 9. GET /api/v1/agents/{id}/metrics - Get agent usage metrics

Gets usage metrics and analytics for a specific agent.

**Response:**
```json
{
  "metrics": {
    "total_tasks": 150,
    "completed_tasks": 135,
    "failed_tasks": 15,
    "success_rate": 90,
    "avg_execution_time_ms": 2450,
    "total_tokens_used": 45000,
    "total_cost_usd": 3.75,
    "tasks_by_status": {
      "pending": 5,
      "running": 2,
      "completed": 135,
      "failed": 15,
      "cancelled": 3
    },
    "tasks_by_hour": {
      "00:00": 2,
      "01:00": 1,
      "02:00": 0,
      "03:00": 1,
      "04:00": 0,
      "05:00": 3,
      "06:00": 5,
      "07:00": 8,
      "08:00": 12,
      "09:00": 15,
      "10:00": 18,
      "11:00": 10,
      "12:00": 8,
      "13:00": 7,
      "14:00": 6,
      "15:00": 5,
      "16:00": 4,
      "17:00": 3,
      "18:00": 2,
      "19:00": 1,
      "20:00": 0,
      "21:00": 1,
      "22:00": 0,
      "23:00": 0
    },
    "cost_by_day": {
      "2024-01-01": 0.25,
      "2024-01-02": 0.30,
      "2024-01-03": 0.28,
      "2024-01-04": 0.32,
      "2024-01-05": 0.35,
      "2024-01-06": 0.30,
      "2024-01-07": 0.29
    }
  }
}
```

---

## Authentication

All routes require authentication via JWT token. Include the token in the Authorization header:
```
Authorization: Bearer your-jwt-token
```

## Rate Limiting

All routes implement rate limiting to prevent abuse:
- Create: 10 requests per hour
- Update: 20 requests per hour
- Delete: 20 requests per hour
- Test: 50 requests per hour
- Deploy: 20 requests per hour

## Error Handling

The API returns appropriate HTTP status codes and error messages:
- 200 OK: Successful request
- 201 Created: Resource created successfully
- 400 Bad Request: Invalid input or validation errors
- 401 Unauthorized: Invalid or missing authentication
- 404 Not Found: Resource not found
- 429 Too Many Requests: Rate limit exceeded
- 500 Internal Server Error: Server error

## Response Headers

The API includes rate limiting headers in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Time until reset (in seconds)

## Security

- All communications are over HTTPS
- Input validation and sanitization
- Rate limiting to prevent abuse
- JWT-based authentication
- Proper error handling to prevent information leakage