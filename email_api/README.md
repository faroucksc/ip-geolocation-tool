# Email Provisioning API

FastAPI-based REST API for managing email accounts via DirectAdmin. Built for domain administrators to easily create, delete, and manage email accounts.

## Features

- ✅ JWT-based authentication
- ✅ User registration and login
- ✅ Role-based user management (admin, domain_admin, user)
- ✅ Password reset flow with email notifications
- ✅ List all email accounts
- ✅ Create new email accounts with password validation
- ✅ Delete email accounts (soft delete in DB)
- ✅ Change email passwords (syncs DB + DirectAdmin)
- ✅ Automatic sync with DirectAdmin
- ✅ SMTP email notifications
- ✅ SQLite database for audit trail
- ✅ Docker deployment ready
- ✅ Comprehensive test coverage (31 tests)

## Quick Start

### Prerequisites

- Python 3.12+
- DirectAdmin API credentials
- `uv` package manager (recommended) or `pip`

### Installation

1. Clone the repository
```bash
cd email_provision_tools
```

2. Install dependencies
```bash
uv pip install -r requirements.txt
```

3. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your DirectAdmin credentials
```

4. Run the server
```bash
uv run uvicorn email_api.api.main:app --reload
```

The API will be available at `http://localhost:8000`

## Environment Variables

Create a `.env` file with the following variables:

```bash
# DirectAdmin Configuration
DIRECTADMIN_HOST=https://your-server.mxroute.com:2222
DIRECTADMIN_USER=your_username
DIRECTADMIN_KEY=your_api_key
DEFAULT_DOMAIN=yourdomain.com

# Database
DATABASE_URL=sqlite:///./email.db

# JWT Authentication (Phase 2)
JWT_SECRET=your_secret_key_min_32_chars  # Auto-generated if not set
JWT_EXPIRE_MINUTES=1440  # 24 hours

# Default Admin User
DEFAULT_ADMIN_EMAIL=admin@yourdomain.com
DEFAULT_ADMIN_PASSWORD=ChangeMe123!  # CHANGE THIS IMMEDIATELY
```

**⚠️  Security Note**: On first startup, a default admin user is automatically created. **Change the default password immediately** after first login!

## API Endpoints

### Health Check

```http
GET /health
```

Response:
```json
{
  "status": "ok",
  "service": "email-provisioning-api"
}
```

---

## Authentication Endpoints

All email management endpoints require authentication via JWT token.

### Login

```http
POST /auth/login
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "SecurePass123!"
}
```

Response (200):
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

Errors:
- `401` - Invalid credentials
- `400` - Inactive user

### Register

```http
POST /auth/register
Content-Type: application/json

{
  "email": "newuser@example.com",
  "password": "SecurePass123!",
  "role": "domain_admin",
  "domain": "example.com"
}
```

**Roles:**
- `admin` - Full access to all domains
- `domain_admin` - Access to specific domain only
- `user` - Read-only access (future)

Response (201):
```json
{
  "id": 1,
  "email": "newuser@example.com",
  "role": "domain_admin",
  "domain": "example.com",
  "is_active": true,
  "created_at": "2025-10-03T12:00:00"
}
```

Errors:
- `409` - Email already registered
- `400` - Weak password

### Get Current User

```http
GET /auth/me
Authorization: Bearer <token>
```

Response (200):
```json
{
  "id": 1,
  "email": "user@example.com",
  "role": "domain_admin",
  "domain": "example.com",
  "is_active": true,
  "created_at": "2025-10-03T12:00:00"
}
```

Errors:
- `401` - Invalid/expired token
- `403` - Missing token

---

## Email Management Endpoints

**⚠️  All endpoints require authentication** - Include `Authorization: Bearer <token>` header.

### List Email Accounts

```http
GET /emails
Authorization: Bearer <token>
```

Response:
```json
[
  {
    "id": 1,
    "username": "john",
    "domain": "example.com",
    "quota_mb": 1000,
    "created_at": "2025-10-03T12:00:00",
    "updated_at": "2025-10-03T12:00:00"
  }
]
```

### Create Email Account

```http
POST /emails
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "john",
  "password": "SecurePass123!",
  "quota_mb": 1000
}
```

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number

Response (201):
```json
{
  "id": 1,
  "username": "john",
  "domain": "example.com",
  "quota_mb": 1000,
  "created_at": "2025-10-03T12:00:00",
  "updated_at": "2025-10-03T12:00:00"
}
```

Errors:
- `400` - Weak password
- `409` - Email already exists
- `500` - DirectAdmin error

### Delete Email Account

```http
DELETE /emails/{username}
Authorization: Bearer <token>
```

Response (200):
```json
{
  "message": "Email john@example.com deleted successfully"
}
```

Errors:
- `404` - Email not found
- `500` - DirectAdmin error

### Change Email Password

```http
PUT /emails/{username}/password
Authorization: Bearer <token>
Content-Type: application/json

{
  "new_password": "NewSecurePass456!"
}
```

Response (200):
```json
{
  "message": "Password updated for john@example.com"
}
```

Errors:
- `400` - Weak password
- `404` - Email not found
- `500` - DirectAdmin error

## Interactive Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=email_api

# Run specific test file
uv run pytest email_api/tests/test_api.py

# Run with verbose output
uv run pytest -v
```

## Development

### Project Structure

```
email_provision_tools/
├── email_api/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI app & endpoints
│   │   ├── client.py         # DirectAdmin API client
│   │   ├── database.py       # Database setup
│   │   └── models.py         # SQLModel & Pydantic models
│   └── tests/
│       ├── __init__.py
│       └── test_api.py       # API endpoint tests
├── requirements.txt
├── .env
├── .env.example
└── README.md
```

### Code Quality

```bash
# Run linter
uv run ruff check email_api/

# Format code
uv run ruff format email_api/
```

## Database Schema

### User Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| email | STRING | User email (unique, indexed) |
| hashed_password | STRING | Bcrypt hashed password |
| role | ENUM | User role (admin/domain_admin/user) |
| domain | STRING | Assigned domain (for domain_admin) |
| is_active | BOOLEAN | Account status |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update timestamp |

**Constraints:**
- Unique: email

### EmailAccount Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| username | STRING | Email username (indexed) |
| domain | STRING | Email domain (indexed) |
| quota_mb | INTEGER | Email quota in MB |
| created_by_user_id | INTEGER | Foreign key to User |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update timestamp |
| deleted_at | DATETIME | Soft delete timestamp |

**Constraints:**
- Unique: (username, domain)
- Foreign Key: created_by_user_id → users.id

## Roadmap

### Phase 1 ✅
- [x] Basic CRUD operations
- [x] DirectAdmin integration
- [x] Database persistence
- [x] Password validation
- [x] Comprehensive tests (13 tests)

### Phase 2 ✅
- [x] User authentication (JWT)
- [x] User registration
- [x] Login/logout endpoints
- [x] Protected API endpoints
- [x] Default admin user creation
- [x] Password hashing (bcrypt)
- [x] Authentication tests (18 additional tests)

### Phase 3
- [ ] Role-based access control
- [ ] Domain admin scoping
- [ ] Admin user management

### Phase 4
- [ ] React frontend UI
- [ ] Email management dashboard

### Phase 5
- [ ] MCP server integration
- [ ] AI-assisted management

## Troubleshooting

### SSL Certificate Errors

If you encounter SSL certificate errors with DirectAdmin:
```bash
# The client disables SSL verification for self-signed certs
# This is configured in client.py: verify=False
```

### Database Locked

If you get "database is locked" errors:
```bash
# Stop all running instances
pkill -f uvicorn

# Remove lock
rm email.db
```

### DirectAdmin API Errors

Check your API key permissions in DirectAdmin panel:
- `CMD_API_SHOW_DOMAINS` - Required to list domains
- `CMD_API_POP` - Required for email operations
- `CMD_CHANGE_EMAIL_PASSWORD` - Required for password changes

## Contributing

1. Create feature branch
2. Make changes
3. Run tests: `uv run pytest`
4. Run linter: `uv run ruff check`
5. Submit pull request

## License

MIT

## Support

For issues or questions:
- GitHub Issues: [project-url]/issues
- Documentation: See `ai_docs/` folder
