# Email Provisioning Tools - Project Brief

## Problem Statement
Domain administrators need a simple way to manage email accounts (create/delete/password changes) without navigating complex DirectAdmin interfaces. Current solutions are either too complex or lack proper access control.

## Solution
Build a minimal FastAPI-based email management system with role-based access control, following Jeremy Howard's principles of simplicity and progressive disclosure.

## Core Principles (Jeremy Howard Approach)

### 1. **Start Simple, Build Up**
- Begin with working code, not abstractions
- Single file → Multiple files only when necessary
- SQLite first (no PostgreSQL until needed)
- Inline config before .env files

### 2. **Make It Work, Then Make It Good**
- Get CRUD operations working first
- Add auth after basic endpoints proven
- Optimize only when performance matters

### 3. **Minimal Dependencies**
- FastAPI (web framework)
- SQLModel (ORM + validation)
- httpx (DirectAdmin API client)
- python-jose (JWT tokens)
- passlib (password hashing)

### 4. **Progressive Disclosure**
- Phase 1: Basic CRUD (no auth)
- Phase 2: Add authentication
- Phase 3: Add role-based access
- Phase 4: Add UI (React)
- Phase 5: Add MCP server (roadmap)

## Target Users
- **Primary**: Domain administrators managing email accounts for their domain
- **Secondary**: System administrators managing multiple domains

## Success Criteria
1. Domain admin can create/delete email accounts in < 30 seconds
2. All operations sync with DirectAdmin API
3. Audit trail of all email account changes
4. Zero configuration for first run (sensible defaults)

## Out of Scope (v1)
- Email forwarding/aliases
- Spam filter management
- Email client configuration UI
- Multi-tenant support
- Reseller account management

## Technical Constraints
- Must work with MXRoute DirectAdmin API
- Must handle DirectAdmin's URL-encoded responses
- Must support API key authentication (not password)
- Must be deployable as single Python process

## Key Metrics
- API response time < 500ms (excluding DirectAdmin calls)
- Zero downtime deployments
- 100% test coverage for business logic
