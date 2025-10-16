# Password Reset Flow

## Overview

When creating management users (domain_admin/admin), system generates time-limited password reset token and sends email with clickable link. User clicks link, sets new password via HTML form, then auto-redirects to webmail.

## User Journey

### 1. Admin Creates User
```
POST /auth/register
{
  "email": "manager@xseller.io",
  "password": "TempPass123!",
  "role": "domain_admin",
  "domain": "xseller.io",
  "recovery_email": "manager@gmail.com",
  "must_change_password": true
}
```

### 2. System Actions
- Creates user in database
- Generates UUID reset token
- Stores token with 48hr expiry
- Sends email to recovery_email with reset link

### 3. Email Content
```
Your management account has been created.

Login: manager@xseller.io
Temporary Password: TempPass123!

⚠️ IMPORTANT: Change your password before first login.

Reset Password: https://admin.faso.dev/reset-password?token=abc-123-def

(Link expires in 48 hours)

Management Portal: https://admin.faso.dev
```

### 4. User Clicks Link
Browser opens: `https://admin.faso.dev/reset-password?token=abc-123-def`

Backend serves HTML form:
```html
<!DOCTYPE html>
<html>
<head>
    <title>Change Your Password</title>
    <style>/* Simple CSS */</style>
</head>
<body>
    <form method="POST" action="/reset-password">
        <h1>Change Your Password</h1>
        <input type="hidden" name="token" value="abc-123-def">
        <input type="password" name="new_password" placeholder="New Password" required>
        <input type="password" name="confirm_password" placeholder="Confirm Password" required>
        <button type="submit">Change Password</button>
    </form>
</body>
</html>
```

### 5. User Submits Form
```
POST /reset-password
{
  "token": "abc-123-def",
  "new_password": "MySecurePass456!",
  "confirm_password": "MySecurePass456!"
}
```

### 6. Backend Validation
- Token exists & not expired & not used
- Passwords match
- Password meets requirements (8+ chars, uppercase, lowercase, digit)
- Updates user password in DB
- Updates email password in DirectAdmin (if email account exists)
- Marks token as used
- Sets `must_change_password = false`

### 7. Success Redirect
```http
HTTP/1.1 302 Found
Location: https://webmail.xseller.io?message=password_changed
```

User lands at webmail with success message.

---

## Database Schema

### PasswordResetToken Table
```sql
CREATE TABLE password_reset_tokens (
  token VARCHAR PRIMARY KEY,
  user_id INTEGER FOREIGN KEY REFERENCES users(id),
  expires_at TIMESTAMP NOT NULL,
  used BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Endpoints

### GET /reset-password?token={token}
**Returns:** HTML form
**Validation:**
- Token exists
- Not expired
- Not used

**Error Cases:**
- Token invalid/expired → HTML error page: "Link expired. Contact admin."
- Token already used → HTML error page: "Link already used."

### POST /reset-password
**Content-Type:** application/x-www-form-urlencoded
**Body:**
```
token=abc-123-def
new_password=SecurePass456!
confirm_password=SecurePass456!
```

**Success:** 302 redirect to webmail
**Error:** HTML error page with message

---

## Security Considerations

1. **Token Expiry:** 48 hours (configurable)
2. **Single Use:** Token marked as used after successful reset
3. **UUID Tokens:** Cryptographically random, unpredictable
4. **HTTPS Only:** Reset links require HTTPS in production
5. **Rate Limiting:** Max 5 reset attempts per hour per user (future)
6. **Email Verification:** Only sent to `recovery_email` (not login email)

---

## Email Account vs Management Account

**Management Account (domain_admin/admin):**
- Gets reset token link
- Changes password via web form
- Redirects to admin portal or webmail
- Password stored in database only

**Email Account (created via POST /emails):**
- Gets IMAP/SMTP credentials
- No reset token (use webmail password reset)
- Password stored in DirectAdmin
- Optional: notify_email gets account details

---

## Configuration

### Environment Variables
```bash
# Password reset token expiry (hours)
RESET_TOKEN_EXPIRY_HOURS=48

# Webmail redirect URL (after password reset)
WEBMAIL_URL=https://webmail.xseller.io

# API base URL (for reset links in emails)
API_BASE_URL=https://admin.faso.dev
```

---

## Implementation Files

- `email_api/api/models.py` - PasswordResetToken model
- `email_api/api/main.py` - GET/POST /reset-password endpoints
- `email_api/api/email_service.py` - Email template with reset link
- `email_api/templates/reset_password.html` - HTML form template
- `email_api/ai_docs/password_reset_flow.md` - This documentation
