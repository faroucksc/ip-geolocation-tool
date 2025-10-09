# PHASE 2: Add Authentication

**Goal**: Add JWT-based authentication with user management
**Status**: Not Started
**Dependencies**: PHASE_1 (completed)
**Estimated Duration**: 2-3 hours

---

## Tasks Checklist

### Setup (0.5 hour)

- [ ] Install additional dependencies
  - [ ] `python-jose[cryptography]` (JWT tokens)
  - [ ] `passlib[bcrypt]` (password hashing)
  - [ ] `python-multipart` (form data)
- [ ] Update `requirements.txt`

---

### C4: Authentication Layer (2 hours)

**Files**:
- `email_api/api/models.py` (add User model)
- `email_api/api/auth.py` (new file)

#### Update Models (M1 from PRD)

**File**: `email_api/api/models.py`

- [ ] Create `User` SQLModel
  - [ ] `id` (primary key)
  - [ ] `email` (unique, not null)
  - [ ] `hashed_password` (not null)
  - [ ] `role` (enum: admin, domain_admin, user)
  - [ ] `domain` (nullable, for domain_admin)
  - [ ] `is_active` (boolean, default True)
  - [ ] `created_at`, `updated_at`
- [ ] Create Pydantic request/response models:
  - [ ] `UserResponse` (exclude hashed_password)
  - [ ] `LoginRequest` (email, password)
  - [ ] `RegisterRequest` (email, password, role, domain)
  - [ ] `TokenResponse` (access_token, token_type, expires_in)

#### Authentication Module

**File**: `email_api/api/auth.py`

- [ ] Password hashing functions:
  - [ ] `hash_password(password: str) -> str`
  - [ ] `verify_password(plain: str, hashed: str) -> bool`
- [ ] JWT token functions:
  - [ ] `create_access_token(data: dict, expires_delta: timedelta) -> str`
  - [ ] `decode_access_token(token: str) -> dict`
- [ ] Auth dependencies:
  - [ ] `get_current_user(token: str, session: Session) -> User`
  - [ ] `get_current_active_user(user: User) -> User`
- [ ] Generate JWT secret in .env if not exists

**Acceptance Criteria**:
- ✓ Passwords hashed with bcrypt
- ✓ JWT tokens include user_id, email, role
- ✓ Tokens expire after 24 hours (configurable)
- ✓ Can decode and verify tokens

---

### API Endpoints - Authentication (1.5 hours)

**File**: `email_api/api/main.py`

#### E5: Login - `POST /auth/login`

- [ ] Implement endpoint
- [ ] Validate credentials (email + password)
- [ ] Verify password hash
- [ ] Generate JWT token
- [ ] Return TokenResponse
- [ ] Handle errors:
  - [ ] 401 for invalid credentials
  - [ ] 400 for inactive users

**Request:**
```json
{
  "email": "admin@example.com",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

#### E6: Register - `POST /auth/register`

- [ ] Implement endpoint
- [ ] Validate request (RegisterRequest)
- [ ] Check if email already exists (409)
- [ ] Hash password
- [ ] Create user in database
- [ ] Return UserResponse
- [ ] Handle errors:
  - [ ] 409 for duplicate email
  - [ ] 400 for invalid input

**Request:**
```json
{
  "email": "newuser@example.com",
  "password": "SecurePass123!",
  "role": "domain_admin",
  "domain": "xseller.io"
}
```

**Response:**
```json
{
  "id": 1,
  "email": "newuser@example.com",
  "role": "domain_admin",
  "domain": "xseller.io",
  "is_active": true,
  "created_at": "2025-10-03T12:00:00"
}
```

#### E7: Get Current User - `GET /auth/me`

- [ ] Implement endpoint
- [ ] Require authentication (Bearer token)
- [ ] Return current user info (UserResponse)
- [ ] Handle errors:
  - [ ] 401 for invalid/missing token

**Headers:**
```
Authorization: Bearer eyJhbGc...
```

**Response:**
```json
{
  "id": 1,
  "email": "admin@example.com",
  "role": "admin",
  "domain": null,
  "is_active": true,
  "created_at": "2025-10-03T12:00:00"
}
```

#### Update Email Endpoints

- [ ] Update `EmailAccount` model to include `created_by_user_id` FK
- [ ] Make email endpoints require authentication:
  - [ ] `GET /emails` - require auth
  - [ ] `POST /emails` - require auth, set created_by_user_id
  - [ ] `DELETE /emails/{username}` - require auth
  - [ ] `PUT /emails/{username}/password` - require auth

**Acceptance Criteria**:
- ✓ All email endpoints protected by JWT auth
- ✓ Unauthenticated requests return 401
- ✓ created_by_user_id tracked for audit

---

### Database Migration (0.5 hour)

**File**: `email_api/api/database.py`

- [ ] Add `User` table creation
- [ ] Add migration logic for existing `EmailAccount` records
  - [ ] Add `created_by_user_id` column (nullable)
  - [ ] Keep existing records (NULL for created_by)
- [ ] Create default admin user on first startup:
  - [ ] Email: from env `DEFAULT_ADMIN_EMAIL`
  - [ ] Password: from env `DEFAULT_ADMIN_PASSWORD`
  - [ ] Role: `admin`
  - [ ] Only if no users exist

**Environment Variables:**
```bash
JWT_SECRET=<auto-generate-if-missing>
JWT_EXPIRE_MINUTES=1440  # 24 hours
DEFAULT_ADMIN_EMAIL=admin@xseller.io
DEFAULT_ADMIN_PASSWORD=ChangeMe123!
```

**Acceptance Criteria**:
- ✓ User table created on startup
- ✓ Default admin user auto-created
- ✓ Foreign key relationship works

---

### Testing (2 hours)

**File**: `email_api/tests/test_auth.py` (new)

#### Setup
- [ ] Create test fixtures:
  - [ ] `test_user` (creates test user)
  - [ ] `auth_headers` (returns Bearer token headers)
  - [ ] `admin_user` (creates admin user)

#### Tests (mapped to PRD)

- [ ] **T6**: Test user login
  - [ ] Valid credentials return token
  - [ ] Invalid email returns 401
  - [ ] Invalid password returns 401
  - [ ] Inactive user returns 401

- [ ] **T7**: Test token expiration
  - [ ] Fresh token is valid
  - [ ] Expired token returns 401
  - [ ] Token includes correct claims

- [ ] Test user registration:
  - [ ] Valid registration creates user
  - [ ] Duplicate email returns 409
  - [ ] Password is hashed (not plain text)
  - [ ] Weak password rejected

- [ ] Test get current user:
  - [ ] Valid token returns user info
  - [ ] No token returns 401
  - [ ] Invalid token returns 401

- [ ] Test protected endpoints:
  - [ ] GET /emails requires auth
  - [ ] POST /emails requires auth
  - [ ] DELETE /emails/{username} requires auth
  - [ ] PUT /emails/{username}/password requires auth

- [ ] Test password hashing:
  - [ ] hash_password returns bcrypt hash
  - [ ] verify_password validates correctly
  - [ ] Same password different hashes

**File**: `email_api/tests/test_api.py` (update)

- [ ] Update existing tests to use authentication:
  - [ ] Add auth headers to all requests
  - [ ] Create test user before tests
  - [ ] Verify created_by_user_id is set

**Acceptance Criteria**:
- ✓ All tests pass
- ✓ Test coverage > 80%
- ✓ Can run with `pytest`

---

### Documentation (0.5 hour)

- [ ] Update `email_api/README.md`
  - [ ] Add authentication section
  - [ ] Document new endpoints
  - [ ] Add example auth flow
  - [ ] Update environment variables
- [ ] Update `.env.example`
  - [ ] Add JWT_SECRET
  - [ ] Add JWT_EXPIRE_MINUTES
  - [ ] Add DEFAULT_ADMIN_EMAIL
  - [ ] Add DEFAULT_ADMIN_PASSWORD
- [ ] Create `email_api/ai_docs/auth_flow.md`
  - [ ] Registration flow
  - [ ] Login flow
  - [ ] Using tokens
  - [ ] Token refresh (future)

---

## Definition of Done

- [ ] All checklist items completed
- [ ] All tests passing (`pytest`)
- [ ] User can register and login
- [ ] All email endpoints require authentication
- [ ] JWT tokens work correctly
- [ ] Default admin user auto-created
- [ ] No linting errors (`ruff check`)
- [ ] Documentation updated
- [ ] Manual E2E test completed:
  1. Start fresh server
  2. Verify default admin created
  3. Login as admin → get token
  4. Use token to list emails
  5. Register new domain_admin
  6. Login as domain_admin
  7. Create email with auth
  8. Verify created_by_user_id set
  9. Try accessing without token → 401

---

## Dependencies to Add

```txt
# requirements.txt (additions)
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.17
```

---

## Environment Variables (additions)

```bash
# .env (additions)
JWT_SECRET=<will-auto-generate-if-missing>
JWT_EXPIRE_MINUTES=1440
DEFAULT_ADMIN_EMAIL=admin@xseller.io
DEFAULT_ADMIN_PASSWORD=ChangeMe123!
```

---

## Security Considerations

1. **Password Storage**: Never store plain text passwords
2. **JWT Secret**: Must be strong, random, kept secret
3. **Token Expiry**: Tokens should expire (24h default)
4. **HTTPS Only**: In production, enforce HTTPS for auth
5. **Password Requirements**: Already enforced (Phase 1)
6. **Default Admin**: Must change default password immediately

---

## Notes

- JWT tokens are stateless (no database lookup per request)
- Token refresh endpoint can be added in future
- Role-based permissions will be Phase 3
- For now, all authenticated users can do everything
- Phase 3 will add domain scoping for domain_admin role
