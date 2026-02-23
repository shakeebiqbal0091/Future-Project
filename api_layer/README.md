# AI Agent Orchestration Platform API

A comprehensive RESTful API for managing AI agents, workflows, and tasks with full CRUD operations, authentication, and real-time capabilities.

## 🚀 Features

### Core API Endpoints
- **Auth API** (`/api/v1/auth/`): User registration, login, logout, token refresh
- **User API** (`/api/v1/users/`): User profile management, settings
- **Organization API** (`/api/v1/organizations/`): Organization CRUD, membership management
- **Agent API** (`/api/v1/agents/`): Agent creation, management, testing
- **Workflow API** (`/api/v1/workflows/`): Workflow creation, execution, management
- **Task API** (`/api/v1/tasks/`): Task execution, status, logs
- **Integration API** (`/api/v1/integrations/`): Integration setup, management
- **Analytics API** (`/api/v1/analytics/`): Usage metrics, performance data
- **Billing API** (`/api/v1/billing/`): Subscription management, usage tracking

### API Features
- **RESTful Design**: Consistent HTTP methods and status codes
- **Authentication & Authorization**: JWT-based security with role-based access control
- **Validation**: Pydantic schemas for request/response validation
- **Pagination**: Built-in pagination for list endpoints
- **Filtering & Sorting**: Advanced query capabilities
- **WebSocket Support**: Real-time updates for workflows and tasks
- **Rate Limiting**: Protection against abuse
- **Comprehensive Error Handling**: Detailed error responses with proper status codes

## 📋 API Documentation

### OpenAPI/Swagger
- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI JSON**: `/openapi.json`

### Authentication
- JWT tokens with 30-minute expiration
- Refresh token endpoint
- Role-based access control (user, admin, superuser)

### Response Format
```json
{
  "data": {...},
  "message": "Success message",
  "status": "success|error",
  "timestamp": "2026-02-21T10:00:00Z"
}
```

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- PostgreSQL (recommended) or SQLite

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd api_layer
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Database setup**
   ```bash
   # Create database (PostgreSQL)
   createdb ai_agent_platform

   # Run migrations (if using Alembic)
   alembic upgrade head
   ```

5. **Start the API**
   ```bash
   # Development
   python main.py

   # Production with uvicorn
   uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

## 🔧 Configuration

### Environment Variables

```env
# Database
DATABASE_URL=sqlite:///./test.db
# For PostgreSQL: postgresql://user:password@localhost/dbname

# Security
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
DEBUG=false
WORKERS=1

# Stripe (for billing)
STRIPE_SECRET_KEY=your-stripe-secret-key
STRIPE_PUBLISHABLE_KEY=your-stripe-publishable-key

# Email (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com
FROM_NAME=AI Agent Platform
```

## 🏗️ Project Structure

```
api_layer/
├── main.py                    # Main FastAPI application
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── tests/                     # Test suite
├── shared/                    # Shared modules
│   ├── database.py           # Database setup
│   ├── models.py             # SQLAlchemy models
│   ├── schemas.py            # Pydantic schemas
│   ├── security.py           # Authentication & security
│   ├── utils.py              # Utility functions
│   └── __init__.py
├── core/                      # Core functionality
│   ├── router.py             # Core API router
│   ├── middleware.py         # Middleware
│   ├── middleware_setup.py   # Middleware setup
│   └── __init__.py
├── auth.py                    # Authentication API
├── user.py                    # User management API
├── organization.py            # Organization API
├── agent.py                   # Agent management API
├── workflow.py                # Workflow API
├── task.py                    # Task management API
├── integration.py             # Integration API
├── analytics.py               # Analytics API
├── billing.py                 # Billing API
└── __init__.py
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=.

# Run specific test file
pytest tests/test_api.py

# Run with verbose output
pytest tests/ -v
```

### Test Coverage
- Unit tests for all API endpoints
- Integration tests for database operations
- Authentication and authorization tests
- Error handling tests

## 🚀 Deployment

### Docker Deployment

1. **Build Docker image**
   ```bash
   docker build -t ai-agent-platform .
   ```

2. **Run with Docker Compose**
   ```yaml
   # docker-compose.yml
   version: '3.8'
   services:
     api:
       build: .
       ports:
         - "8000:8000"
       environment:
         - DATABASE_URL=postgresql://user:password@postgres/dbname
         - SECRET_KEY=your-secret-key
       depends_on:
         - postgres

     postgres:
       image: postgres:15
       environment:
         POSTGRES_USER: user
         POSTGRES_PASSWORD: password
         POSTGRES_DB: dbname
       ports:
         - "5432:5432"
   ```

3. **Deploy**
   ```bash
   docker-compose up -d
   ```

### Environment-Specific Configuration

#### Development
```bash
# .env.development
DEBUG=true
DATABASE_URL=sqlite:///./dev.db
WORKERS=1
```

#### Production
```bash
# .env.production
DEBUG=false
DATABASE_URL=postgresql://user:password@postgres:5432/dbname
WORKERS=4
SECRET_KEY=your-production-secret-key
```

## 📊 API Usage Examples

### Authentication
```bash
# Register
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "user123",
    "password": "securepassword"
  }'

# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword"
  }'
```

### Organization Management
```bash
# Create organization (requires auth token)
curl -X POST "http://localhost:8000/api/v1/organizations/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Organization",
    "slug": "my-org",
    "description": "My awesome organization"
  }'
```

### Agent Management
```bash
# Create agent
curl -X POST "http://localhost:8000/api/v1/agents/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My OpenAI Agent",
    "type": "openai",
    "model": "gpt-3.5-turbo",
    "api_key": "sk-test-123",
    "organization_id": 1
  }'
```

### Workflow Execution
```bash
# Execute workflow
curl -X POST "http://localhost:8000/api/v1/workflows/1/execute" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "input_data": {"prompt": "Hello world"},
    "async_execution": true
  }'
```

## 🔐 Security

### Authentication
- JWT tokens with configurable expiration
- Password hashing with bcrypt
- Secure token verification

### Authorization
- Role-based access control
- Organization-based permissions
- Superuser privileges

### Rate Limiting
- Configurable rate limits per endpoint
- Protection against abuse
- IP-based tracking

### Input Validation
- Pydantic schema validation
- SQL injection prevention
- XSS protection

## 📊 Monitoring & Analytics

### Built-in Metrics
- Request/response logging
- Performance monitoring
- Error tracking
- Usage analytics

### Custom Analytics
- Token usage tracking
- Task execution metrics
- Cost analysis
- Performance reports

## 🔄 Real-time Features

### WebSocket Support
- Workflow monitoring
- Task status updates
- Real-time notifications
- Live analytics

### Event Streaming
- Task lifecycle events
- Workflow execution events
- Integration activity

## 📦 Integration

### Third-party Integrations
- Slack notifications
- Microsoft Teams
- Email notifications
- Webhook support
- GitHub/GitLab integration

### Custom Integrations
- REST API endpoints
- Custom webhook handlers
- Plugin architecture

## 🔄 WebSocket Endpoints

### Workflow Monitoring
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/workflows/1/ws');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Workflow update:', data);
};
```

### Real-time Notifications
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/notifications');
ws.onmessage = (event) => {
  const notification = JSON.parse(event.data);
  showNotification(notification);
};
```

## 📝 Development Guidelines

### Code Style
- Follow PEP 8 guidelines
- Use type hints
- Write comprehensive docstrings
- Follow RESTful conventions

### Error Handling
- Use appropriate HTTP status codes
- Provide detailed error messages
- Log all errors appropriately
- Implement proper exception handling

### Security Best Practices
- Never expose sensitive data in responses
- Validate all inputs
- Use parameterized queries
- Implement proper authentication

## 🚀 Performance

### Optimization
- Database connection pooling
- Query optimization
- Caching strategies
- Async support where appropriate

### Scalability
- Horizontal scaling support
- Load balancing
- Database sharding considerations
- Microservices architecture ready

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

- **Documentation**: [API Documentation](http://localhost:8000/docs)
- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **Email**: support@aiagentplatform.com