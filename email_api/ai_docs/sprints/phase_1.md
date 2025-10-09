# PHASE 1: Core CRUD (No Auth)

**Goal**: Get basic email operations working with DirectAdmin
**Status**: Not Started
**Dependencies**: None
**Estimated Duration**: 1-2 days

---

## Tasks Checklist

### Setup (0.5 hour)
- [ ] Create project structure
  - [ ] `email/api/` directory
  - [ ] `email/tests/` directory
  - [ ] `requirements.txt`
  - [ ] `.env.example`
- [ ] Install dependencies
  - [ ] fastapi
  - [ ] uvicorn
  - [ ] sqlmodel
  - [ ] httpx
  - [ ] pytest
  - [ ] python-dotenv
- [ ] Create `.env` from creds.md
- [ ] Verify DirectAdmin credentials work

---

### C1: DirectAdmin Client (2 hours)

**File**: `email/api/client.py`

- [ ] Create `DirectAdminClient` class
  - [ ] `__init__(host, user, key, domain)`
  - [ ] `_make_request(endpoint, params)` - Base HTTP method
  - [ ] Handle URL-encoded responses
  - [ ] Add retry logic (3 attempts)
- [ ] Implement email operations:
  - [ ] `list_emails() -> list[dict]`
  - [ ] `create_email(username, password, quota_mb) -> dict`
  - [ ] `delete_email(username) -> bool`
  - [ ] `change_password(username, new_password) -> bool`
- [ ] Add error handling:
  - [ ] Parse DirectAdmin error responses
  - [ ] Raise custom exceptions (`DirectAdminError`)
- [ ] Manual test each method with xseller.io

**Acceptance Criteria**:
- ✓ Can list all emails from DirectAdmin
- ✓ Can create test email account
- ✓ Can change password for test account
- ✓ Can delete test email account
- ✓ Errors are properly parsed and raised

---

### C2: Database Layer (1.5 hours)

**Files**:
- `email/api/database.py`
- `email/api/models.py`

#### `models.py`
- [ ] Create `EmailAccount` SQLModel
  - [ ] All fields from M2 in PRD
  - [ ] Unique constraint on (username, domain)
  - [ ] Soft delete support (deleted_at field)
- [ ] Create Pydantic request/response models:
  - [ ] `EmailAccountResponse` (for API responses)
  - [ ] `CreateEmailRequest` (username, password, quota_mb)
  - [ ] `ChangePasswordRequest` (new_password)

#### `database.py`
- [ ] SQLite connection setup
- [ ] `get_engine()` function
- [ ] `create_db_and_tables()` function
- [ ] `get_session()` dependency for FastAPI
- [ ] Test database creation

**Acceptance Criteria**:
- ✓ Database file created at `./email.db`
- ✓ Tables created with correct schema
- ✓ Can insert/query EmailAccount records
- ✓ Unique constraint enforced

---

### C3: API Endpoints (3 hours)

**File**: `email/api/main.py`

#### Setup
- [ ] Create FastAPI app instance
- [ ] Add CORS middleware
- [ ] Add startup event (create DB tables)
- [ ] Add health check endpoint: `GET /health`

#### Email Endpoints

##### E1: List Emails - `GET /emails`
- [ ] Implement endpoint
- [ ] Call DirectAdmin client
- [ ] Sync with database (upsert logic)
- [ ] Return list of EmailAccountResponse
- [ ] Add error handling

##### E2: Create Email - `POST /emails`
- [ ] Implement endpoint
- [ ] Validate request (CreateEmailRequest)
- [ ] Check password strength (min 8 chars, mixed case, number)
- [ ] Call DirectAdmin create_email
- [ ] Save to database
- [ ] Return EmailAccountResponse
- [ ] Handle errors:
  - [ ] 400 for weak password
  - [ ] 409 for duplicate email
  - [ ] 500 for DirectAdmin errors

##### E3: Delete Email - `DELETE /emails/{username}`
- [ ] Implement endpoint
- [ ] Call DirectAdmin delete_email
- [ ] Soft delete in database (set deleted_at)
- [ ] Return success message
- [ ] Handle errors:
  - [ ] 404 if email not found
  - [ ] 500 for DirectAdmin errors

##### E4: Change Password - `PUT /emails/{username}/password`
- [ ] Implement endpoint
- [ ] Validate request (ChangePasswordRequest)
- [ ] Check password strength
- [ ] Call DirectAdmin change_password
- [ ] Update updated_at in database
- [ ] Return success message
- [ ] Handle errors:
  - [ ] 400 for weak password
  - [ ] 404 if email not found
  - [ ] 500 for DirectAdmin errors

**Acceptance Criteria**:
- ✓ All 4 endpoints return correct HTTP status codes
- ✓ Database syncs with DirectAdmin state
- ✓ Validation errors return 400 with clear messages
- ✓ DirectAdmin errors return 500 with details
- ✓ Can test all endpoints via Swagger UI

---

### Testing (2 hours)

**File**: `email/tests/test_api.py`

#### Setup
- [ ] Configure pytest
- [ ] Create test fixtures:
  - [ ] `test_db` (in-memory SQLite)
  - [ ] `client` (FastAPI TestClient)
  - [ ] `mock_directadmin` (httpx mock)

#### Tests (mapped to PRD)

- [ ] **T1**: Test list emails endpoint
  - [ ] Returns empty list when no emails
  - [ ] Returns emails from DirectAdmin
  - [ ] Syncs database with DirectAdmin state

- [ ] **T2**: Test create email success
  - [ ] Creates email in DirectAdmin
  - [ ] Saves to database
  - [ ] Returns 201 with EmailAccountResponse

- [ ] **T3**: Test create email with duplicate username
  - [ ] Returns 409 error
  - [ ] Does not create duplicate in DB

- [ ] **T4**: Test delete email
  - [ ] Deletes from DirectAdmin
  - [ ] Soft deletes in database
  - [ ] Returns 200 with success message

- [ ] **T5**: Test password change
  - [ ] Changes password in DirectAdmin
  - [ ] Updates updated_at in database
  - [ ] Returns 200 with success message

- [ ] Additional validation tests:
  - [ ] Weak password rejected (< 8 chars)
  - [ ] Weak password rejected (no uppercase)
  - [ ] Weak password rejected (no number)

**Acceptance Criteria**:
- ✓ All tests pass
- ✓ Test coverage > 80%
- ✓ Can run with `pytest`

---

### Documentation (0.5 hour)

- [ ] Create `email/README.md`
  - [ ] Installation instructions
  - [ ] Environment variables
  - [ ] Run commands
  - [ ] API endpoints documentation
- [ ] Update `requirements.txt` with exact versions
- [ ] Create `.env.example` template

---

## Definition of Done

- [ ] All checklist items completed
- [ ] All tests passing (`pytest`)
- [ ] Can create/list/delete/change password via API
- [ ] Database syncs with DirectAdmin
- [ ] No linting errors (`ruff check`)
- [ ] Documentation complete
- [ ] Manual E2E test completed:
  1. Start server: `uvicorn email.api.main:app --reload`
  2. Open Swagger: `http://localhost:8000/docs`
  3. Create test email
  4. Verify in DirectAdmin panel
  5. Change password
  6. Delete email
  7. Verify deletion in DirectAdmin panel

---

## Dependencies Installed

```txt
# requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.32.0
sqlmodel==0.0.22
httpx==0.28.1
pytest==8.3.4
python-dotenv==1.0.1
ruff==0.9.2
```

---

## Environment Variables

```bash
# .env
DIRECTADMIN_HOST=https://london.mxroute.com:2222
DIRECTADMIN_USER=akilyxco
DIRECTADMIN_KEY=5AjJxaXnCErVVCVwkxXn
DEFAULT_DOMAIN=xseller.io
DATABASE_URL=sqlite:///./email.db
```

---

## Notes

- Start simple: Single file `main.py` if possible
- No premature optimization
- Test with real DirectAdmin API (not mocks) first
- Add mocks only after real API proven to work
- Keep password validation simple (defer complex rules to Phase 2)
