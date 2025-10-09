# PHASE 3: Role-Based Access Control

**Goal**: Implement domain scoping and role-based permissions
**Status**: Not Started
**Dependencies**: PHASE_2 (completed)
**Estimated Duration**: 2-3 hours

---

## Tasks Checklist

### C5: Authorization Layer (2 hours)

**File**: `email_api/api/permissions.py` (new)

#### Permission Decorators

- [ ] Create permission checking functions:
  - [ ] `require_role(allowed_roles: list[UserRole])` - Check user has required role
  - [ ] `check_domain_access(user: User, domain: str)` - Verify domain access
  - [ ] `get_user_domains(user: User) -> list[str]` - Get accessible domains
- [ ] Permission helpers:
  - [ ] `can_manage_email(user: User, email_domain: str) -> bool`
  - [ ] `can_access_domain(user: User, domain: str) -> bool`

**Rules:**
- `admin` role: Access to ALL domains
- `domain_admin` role: Access ONLY to assigned domain
- `user` role: Read-only access (future)

**Acceptance Criteria**:
- ✓ Admins can access any domain
- ✓ Domain admins can only access their assigned domain
- ✓ Attempting to access unauthorized domain raises 403
- ✓ Helper functions correctly determine access

---

### Update Email Endpoints with Domain Scoping (1.5 hours)

**File**: `email_api/api/main.py`

#### E1: List Emails - `GET /emails`

**Current behavior**: Lists all emails for DEFAULT_DOMAIN

**New behavior**:
- [ ] Add optional query param: `?domain=example.com`
- [ ] If user is `admin`:
  - [ ] If domain param provided: list emails for that domain
  - [ ] If no domain param: list emails for DEFAULT_DOMAIN
- [ ] If user is `domain_admin`:
  - [ ] Ignore domain param (security)
  - [ ] Always list emails for user's assigned domain only
  - [ ] Return 403 if requesting different domain
- [ ] Update response to include which domain was queried

**Example requests:**
```bash
# Admin: can query any domain
GET /emails?domain=example.com
Authorization: Bearer <admin_token>

# Domain admin: always gets their domain
GET /emails
Authorization: Bearer <domain_admin_token>
# Returns emails for their assigned domain only
```

#### E2: Create Email - `POST /emails`

**Current behavior**: Creates email in DEFAULT_DOMAIN

**New behavior**:
- [ ] Add optional `domain` field to `CreateEmailRequest`
- [ ] If user is `admin`:
  - [ ] If domain provided: create in that domain
  - [ ] If no domain: use DEFAULT_DOMAIN
- [ ] If user is `domain_admin`:
  - [ ] Ignore domain field (security)
  - [ ] Always create in user's assigned domain
  - [ ] Return 403 if domain doesn't match
- [ ] Validate domain exists (optional: check DirectAdmin)

**Example requests:**
```bash
# Admin: can create in any domain
POST /emails
{
  "username": "john",
  "password": "Pass123!",
  "domain": "otherdomain.com"  # Optional
}

# Domain admin: creates in their domain only
POST /emails
{
  "username": "john",
  "password": "Pass123!"
  # domain field ignored, uses user's assigned domain
}
```

#### E3: Delete Email - `DELETE /emails/{username}`

**New behavior**:
- [ ] Add optional query param: `?domain=example.com`
- [ ] Determine email's domain:
  - [ ] If domain param provided: use that
  - [ ] Else: use DEFAULT_DOMAIN or user's assigned domain
- [ ] Check user has permission for that domain
- [ ] If `domain_admin`: verify domain matches their assigned domain
- [ ] Delete from correct domain

#### E4: Change Password - `PUT /emails/{username}/password`

**New behavior**:
- [ ] Same domain scoping logic as delete
- [ ] Verify user has access to email's domain
- [ ] Change password in correct domain

**Acceptance Criteria**:
- ✓ All endpoints respect user role permissions
- ✓ Domain admins cannot access other domains (403)
- ✓ Admins can access any domain
- ✓ Email operations work in correct domain
- ✓ Audit trail includes domain info

---

### Update Models (0.5 hour)

**File**: `email_api/api/models.py`

- [ ] Update `CreateEmailRequest`:
  - [ ] Add optional `domain: Optional[str]` field
  - [ ] Default to None
- [ ] Update `EmailAccountResponse`:
  - [ ] Ensure domain is always included
- [ ] Create `DomainListRequest` (optional):
  - [ ] For filtering by domain

**Example:**
```python
class CreateEmailRequest(SQLModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8)
    quota_mb: int = Field(default=1000, ge=1, le=50000)
    domain: Optional[str] = Field(default=None)  # New field
```

---

### Admin Endpoints (1 hour)

**File**: `email_api/api/main.py`

#### E8: List All Users - `GET /admin/users`

- [ ] Implement endpoint (admin only)
- [ ] Return all users with their roles and domains
- [ ] Support pagination (optional)
- [ ] Filter by role (optional)

**Response:**
```json
[
  {
    "id": 1,
    "email": "admin@example.com",
    "role": "admin",
    "domain": null,
    "is_active": true,
    "created_at": "..."
  },
  {
    "id": 2,
    "email": "domainadmin@example.com",
    "role": "domain_admin",
    "domain": "example.com",
    "is_active": true,
    "created_at": "..."
  }
]
```

#### E9: Update User Role - `PUT /admin/users/{user_id}/role`

- [ ] Implement endpoint (admin only)
- [ ] Allow changing user role
- [ ] Allow changing assigned domain
- [ ] Return updated user

**Request:**
```json
{
  "role": "domain_admin",
  "domain": "newdomain.com"
}
```

#### E10: Deactivate User - `PUT /admin/users/{user_id}/deactivate`

- [ ] Implement endpoint (admin only)
- [ ] Set `is_active = False`
- [ ] Prevent deactivated users from logging in
- [ ] Return updated user

**Acceptance Criteria**:
- ✓ Only admins can access `/admin/*` endpoints
- ✓ Domain admins get 403 on admin endpoints
- ✓ Can list all users
- ✓ Can update user roles
- ✓ Can deactivate/reactivate users

---

### Testing (2 hours)

**File**: `email_api/tests/test_permissions.py` (new)

#### Setup

- [ ] Create test fixtures:
  - [ ] `admin_user` (role=admin, domain=None)
  - [ ] `domain_admin_user` (role=domain_admin, domain="example.com")
  - [ ] `other_domain_admin` (role=domain_admin, domain="other.com")
  - [ ] `admin_headers` (Bearer token for admin)
  - [ ] `domain_admin_headers` (Bearer token for domain_admin)

#### Tests (mapped to PRD)

- [ ] **T8**: Test domain_admin can only access their domain
  - [ ] Can list emails for their domain
  - [ ] Cannot list emails for other domain (403)
  - [ ] Can create email in their domain
  - [ ] Cannot create email in other domain (403)
  - [ ] Can delete email in their domain
  - [ ] Cannot delete email in other domain (403)

- [ ] **T9**: Test admin can access all domains
  - [ ] Can list emails for any domain
  - [ ] Can create email in any domain
  - [ ] Can delete email in any domain
  - [ ] Can change password in any domain

- [ ] Test permission helpers:
  - [ ] `can_manage_email` returns correct boolean
  - [ ] `can_access_domain` respects roles
  - [ ] `get_user_domains` returns correct domains

- [ ] Test admin endpoints:
  - [ ] Non-admin cannot access `/admin/users` (403)
  - [ ] Admin can list all users
  - [ ] Admin can update user roles
  - [ ] Admin can deactivate users

- [ ] Test edge cases:
  - [ ] Domain admin trying to escalate own role (403)
  - [ ] Creating email with domain field as domain_admin (ignored)
  - [ ] Deactivated user cannot login (401)

**File**: `email_api/tests/test_api.py` (update)

- [ ] Update existing tests to work with domain scoping:
  - [ ] Add domain param where needed
  - [ ] Use admin user for tests that need cross-domain access
  - [ ] Add domain-specific test variations

**Acceptance Criteria**:
- ✓ All tests pass
- ✓ Test coverage > 80%
- ✓ Edge cases covered
- ✓ Can run with `pytest`

---

### Documentation (0.5 hour)

- [ ] Update `email_api/README.md`:
  - [ ] Document role permissions
  - [ ] Add domain query parameter examples
  - [ ] Document admin endpoints
  - [ ] Add permission matrix table
- [ ] Create `email_api/ai_docs/permissions.md`:
  - [ ] Explain role-based access control
  - [ ] Permission decision flowchart
  - [ ] Examples for each role
- [ ] Update API examples with domain parameters

**Permission Matrix:**

| Endpoint | Admin | Domain Admin | User |
|----------|-------|--------------|------|
| GET /emails | All domains | Own domain only | Own domain (read) |
| POST /emails | Any domain | Own domain only | ❌ Forbidden |
| DELETE /emails/{username} | Any domain | Own domain only | ❌ Forbidden |
| PUT /emails/{username}/password | Any domain | Own domain only | ❌ Forbidden |
| GET /admin/users | ✅ Allowed | ❌ Forbidden | ❌ Forbidden |
| PUT /admin/users/{id}/role | ✅ Allowed | ❌ Forbidden | ❌ Forbidden |

---

## Definition of Done

- [ ] All checklist items completed
- [ ] All tests passing (`pytest`)
- [ ] Domain admins scoped to their domain
- [ ] Admins can manage all domains
- [ ] Admin endpoints functional
- [ ] No linting errors (`ruff check`)
- [ ] Documentation updated
- [ ] Manual E2E test completed:
  1. Start server
  2. Login as admin
  3. Create domain_admin for domain A
  4. Login as domain_admin
  5. Create email in domain A → success
  6. Try to create email in domain B → 403
  7. Login as admin
  8. Create email in domain B → success
  9. List all users as admin → works
  10. Try to list users as domain_admin → 403
  11. Deactivate domain_admin user
  12. Try to login as deactivated user → 401

---

## Changes Summary

### New Files
- `email_api/api/permissions.py` - Permission checking logic
- `email_api/tests/test_permissions.py` - Permission tests
- `email_api/ai_docs/permissions.md` - Permission documentation

### Modified Files
- `email_api/api/main.py` - Add domain scoping, admin endpoints
- `email_api/api/models.py` - Add domain field to requests
- `email_api/tests/test_api.py` - Update tests for domain scoping
- `email_api/README.md` - Document permissions

### Database Changes
- No schema changes required (User.domain already exists)

---

## Security Considerations

1. **Domain Isolation**: Domain admins MUST NOT bypass domain checks
2. **Parameter Tampering**: Ignore domain param for domain_admin users
3. **Privilege Escalation**: Domain admins cannot change own role
4. **Admin Protection**: Cannot deactivate last admin user
5. **Audit Trail**: Log all permission failures

---

## Notes

- Domain field is optional for admin (backwards compatible)
- Domain admins have domain field ENFORCED
- User role is read-only for now (Phase 4+)
- Permission checks happen BEFORE DirectAdmin calls
- 403 Forbidden for permission denied, 401 for unauthenticated
