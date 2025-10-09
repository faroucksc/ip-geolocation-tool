# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Email provisioning API built with FastAPI that manages email accounts via DirectAdmin. Includes JWT authentication, role-based access control (RBAC), and SQLite persistence. Supports both local development and Docker deployment.

## Key Commands

### Development
```bash
# Run API server locally
uv run uvicorn email_api.api.main:app --reload --port 8000

# Run all tests
uv run pytest

# Run specific test file
uv run pytest email_api/tests/test_auth.py

# Run single test
uv run pytest email_api/tests/test_api.py::test_create_email -v

# Code formatting
uv run ruff format .

# Linting
uv run ruff check .
```

### Docker
```bash
# Build and start
docker-compose up --build

# Start in background
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f
```

## Architecture

### Three-Role RBAC System
- **Admin**: Full access to all domains, can manage users
- **Domain Admin**: Access only to assigned domain
- **User**: Read-only (future)

Domain admins attempting to access other domains via API params triggers 403. See `email_api/api/permissions.py` for enforcement logic.

### Request Flow
1. **Authentication**: JWT token validated via `get_current_active_user()` dependency in `email_api/api/auth.py:156`
2. **Permission Check**: `check_domain_param_tampering()` detects privilege escalation attempts in `email_api/api/permissions.py:128`
3. **Domain Resolution**: `get_effective_domain()` determines target domain in `email_api/api/permissions.py:150`
4. **Access Control**: `check_domain_access()` validates user can access domain in `email_api/api/permissions.py:70`
5. **API Call**: DirectAdmin client executes operation in `email_api/api/client.py`

### DirectAdmin Client
Custom HTTP client (`email_api/api/client.py`) handles:
- URL-encoded response parsing
- Exponential backoff retry logic (3 attempts)
- SSL verification disabled for self-signed certs
- Multi-domain support via client instantiation

### Database Models
Uses SQLModel (SQLAlchemy + Pydantic). Two main tables:
- **User**: Authentication, role, assigned domain
- **EmailAccount**: Email metadata with soft-delete support

Database operations use dependency injection via `get_session()` in `email_api/api/database.py:27`.

### Password Validation
All passwords require 8+ chars, uppercase, lowercase, digit. Enforced in `email_api/api/main.py:202`.

## Configuration

Environment variables (see `.env.example`):
- `DIRECTADMIN_HOST`, `DIRECTADMIN_USER`, `DIRECTADMIN_KEY`: DirectAdmin API credentials
- `DEFAULT_DOMAIN`: Default domain for admin operations
- `JWT_SECRET`: JWT signing key (auto-generated if missing)
- `JWT_EXPIRE_MINUTES`: Token expiration (default: 1440)
- `DEFAULT_ADMIN_EMAIL`, `DEFAULT_ADMIN_PASSWORD`: Default admin user created on first startup

## Testing

Tests use pytest with FastAPI TestClient. Test structure:
- `test_auth.py`: JWT authentication, password hashing
- `test_api.py`: Email CRUD operations
- `test_permissions.py`: RBAC enforcement

All tests in `email_api/tests/` directory. Pytest config in `pytest.ini`.

## Docker

Multi-stage build with `uv` for fast dependency installation. Persistent SQLite volume mounted at `/app/data`. Health check hits `/health` endpoint every 30s.

## Project Structure

```
email_provision_tools/
├── email_api/
│   ├── api/
│   │   ├── main.py          # FastAPI app, endpoints
│   │   ├── models.py        # SQLModel tables + Pydantic schemas
│   │   ├── database.py      # DB session management
│   │   ├── auth.py          # JWT + password hashing
│   │   ├── client.py        # DirectAdmin HTTP client
│   │   └── permissions.py   # RBAC logic
│   └── tests/               # Pytest test suite
├── Dockerfile               # Multi-stage Python 3.12 build
├── docker-compose.yml       # Service + volume config
└── requirements.txt         # Python dependencies
```
