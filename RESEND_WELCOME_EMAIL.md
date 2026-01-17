# Resend Welcome Email Feature

## Overview

Added the ability to resend the welcome email with a new temporary password for customers who:
- Didn't receive the original email
- Let their temporary password expire (7 days)
- Lost or forgot their temporary password
- Never completed their initial login

**Important Restriction:** This endpoint **cannot** be used if the customer has already set their own password (completed initial login). For those customers, use the standard forgot password flow instead.

## New Endpoint

### `POST /customers/{customer_id}/resend-welcome`

**Authentication:** Admin only (requires admin access token)

**Parameters:**
- `customer_id` (path) - The customer's unique ID

**Response:**
```json
{
  "customer_id": "abc123...",
  "email": "customer@example.com",
  "name": "John Doe",
  "temporary_password": "xY9$nMz2!pQ8wE5t",
  "message": "Welcome email resent with new temporary password"
}
```

## How It Works

### 1. Admin Initiates Resend

```bash
POST /customers/{customer_id}/resend-welcome
Authorization: Bearer {admin_token}
```

### 2. System Actions

1. **Generates new temporary password** (16 chars, secure)
2. **Sets password in Cognito** (must be changed on login)
3. **Sends welcome email** to customer automatically
4. **Returns password** to admin as backup

### 3. Customer Receives Email

```
From: no-reply@verificationemail.com
Subject: Welcome to Hovver - Your Account Has Been Created

Hello customer@example.com,

Your Hovver account has been created!

Username: customer@example.com
Temporary Password: xY9$nMz2!pQ8wE5t

Please log in and change your password on first login.

Best regards,
Hovver Team
```

### 4. Customer Must Change Password

When customer logs in with the temporary password, they'll be prompted to set a new permanent password.

## Use Cases

### Case 1: Customer Didn't Receive Original Email

**Scenario:** Customer never got the welcome email (spam filter, wrong email, etc.)

**Solution:**
```bash
POST /customers/{customer_id}/resend-welcome
```

Admin can resend with a new password.

### Case 2: Temporary Password Expired

**Scenario:** Customer waited more than 7 days to login. Password expired.

**Error when customer tries to login:**
```json
{
  "detail": "Temporary password has expired"
}
```

**Solution:**
```bash
POST /customers/{customer_id}/resend-welcome
```

Generates fresh password with new 7-day expiration.

### Case 3: Customer Lost Password

**Scenario:** Customer lost the email with their temporary password.

**Solution:**
```bash
POST /customers/{customer_id}/resend-welcome
```

New password sent via email.

### Case 4: Email Went to Spam

**Scenario:** Original email went to spam folder and was deleted.

**Solution:**
```bash
POST /customers/{customer_id}/resend-welcome
```

Resend the email (customer should check spam).

### Case 5: User Already Changed Password ❌

**Scenario:** Customer successfully logged in and changed their password, but now they forgot it.

**Attempting to resend:**
```bash
POST /customers/{customer_id}/resend-welcome
```

**Error Response:**
```json
{
  "detail": "Cannot resend welcome email. Customer has already set their own password. Use the forgot password flow instead."
}
```

**Correct Solution - Use Forgot Password Flow:**
1. Customer initiates password reset:
   ```bash
   POST /auth/forgot-password
   {
     "username": "customer@example.com"
   }
   ```

2. Customer receives reset code via email

3. Customer resets password:
   ```bash
   POST /auth/reset-password
   {
     "username": "customer@example.com",
     "confirmation_code": "123456",
     "new_password": "NewPassword123!"
   }
   ```

## Admin Workflow

### Via API

```bash
# 1. Get customer ID from customer list
GET /customers

# 2. Resend welcome email
POST /customers/{customer_id}/resend-welcome

# 3. Inform customer to check email
# "Check your email for new login credentials"
```

### Via Postman

1. **Navigate to:** Customer Management → Resend Welcome Email
2. **Ensure** `customer_id` variable is set
3. **Send request**
4. **Check console** for new temporary password
5. **Email is sent automatically** to customer

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `customer_id` | string | Customer's unique ID |
| `email` | string | Customer's email address |
| `name` | string | Customer's name |
| `temporary_password` | string | New temporary password (16 chars) |
| `message` | string | Success message |

## Error Responses

### 400 Bad Request - Password Already Changed
```json
{
  "detail": "Cannot resend welcome email. Customer has already set their own password. Use the forgot password flow instead."
}
```

**Reason:** Customer already completed initial login and changed their password

**Solution:** Use the standard forgot password endpoints:
1. `POST /auth/forgot-password` - Initiates password reset
2. `POST /auth/reset-password` - Completes password reset with code

### 400 Bad Request - Invalid User Status
```json
{
  "detail": "Cannot resend welcome email. User status is {status}. This feature is only for users who haven't completed initial login."
}
```

**Reason:** User is in an unexpected status

**Valid statuses for resend:**
- `FORCE_CHANGE_PASSWORD` - User has temporary password, hasn't changed it yet
- `RESET_REQUIRED` - Password reset is required

**Invalid statuses (cannot resend):**
- `CONFIRMED` - User has set their own password
- Other statuses

### 404 Not Found
```json
{
  "detail": "Customer not found"
}
```

**Reason:** Invalid customer_id

### 403 Forbidden
```json
{
  "detail": "Admin access required"
}
```

**Reason:** Non-admin user attempted to resend

### 500 Internal Server Error
```json
{
  "detail": "Failed to resend welcome email: {error details}"
}
```

**Reason:** AWS Cognito error (check CloudWatch logs)

## Implementation Details

### User Status Validation

Before resending the welcome email, the system checks the Cognito user status to ensure the customer hasn't already set their own password.

**Cognito User Statuses:**

| Status | Description | Resend Allowed? |
|--------|-------------|-----------------|
| `FORCE_CHANGE_PASSWORD` | User has temporary password, must change on login | ✅ YES |
| `RESET_REQUIRED` | Password reset required | ✅ YES |
| `CONFIRMED` | User has set their own password | ❌ NO - Use forgot password instead |
| `UNCONFIRMED` | Email not verified | ❌ NO |
| `ARCHIVED` | User archived | ❌ NO |
| `COMPROMISED` | User compromised | ❌ NO |
| `UNKNOWN` | Unknown status | ❌ NO |

**Why this validation is important:**
- Prevents resetting a customer's permanent password without their consent
- Ensures proper security flow for password recovery
- Differentiates between initial setup (temporary password) and password reset (forgot password)

### Service Method: `resend_customer_welcome()`

Located in: `api/services/auth.py`

**Steps:**
1. Retrieves customer by ID
2. **Checks user status in Cognito** (NEW)
3. **Validates user hasn't set their own password** (NEW)
4. Generates new secure password (uses `_generate_temporary_password()`)
5. Calls `admin_set_user_password()` with `Permanent=False`
6. Calls `admin_create_user()` with `MessageAction='RESEND'`
7. Returns customer details with new password

### Cognito API Calls

```python
# Check user status first
user_response = admin_get_user(
    UserPoolId=user_pool_id,
    Username=email
)

user_status = user_response.get('UserStatus')

# Only allow for users who haven't set their password
if user_status == 'CONFIRMED':
    raise HTTPException(400, "Customer has already set their own password")

# Set new temporary password
admin_set_user_password(
    UserPoolId=user_pool_id,
    Username=email,
    Password=new_password,
    Permanent=False  # Must change on login
)

# Resend welcome email
admin_create_user(
    UserPoolId=user_pool_id,
    Username=email,
    MessageAction='RESEND'  # Triggers email
)
```

## Security Considerations

### ✅ Status Validation
- **Checks user status before allowing resend**
- **Prevents resetting permanent passwords** without user consent
- **Only works for temporary/initial passwords**
- **Protects users who have already set their password**

### ✅ Secure Password Generation
- 16 characters
- Uppercase, lowercase, digits, special chars
- Cryptographically random (Python `secrets`)

### ✅ Admin Only
- Requires admin authentication
- Regular users cannot resend passwords for others

### ✅ Password Expiration
- Temporary password expires in 7 days
- Must be changed on first login

### ✅ Audit Trail
- CloudWatch logs record all password resets
- API returns password for admin records

## Testing

### Test with Postman

1. **Create a test customer:**
   ```json
   POST /customers
   {
     "email": "test@example.com",
     "name": "Test User"
   }
   ```

2. **Wait a moment** (optional)

3. **Resend welcome email:**
   ```
   POST /customers/{customer_id}/resend-welcome
   ```

4. **Check email** at test@example.com

5. **Verify:**
   - ✅ Email received
   - ✅ New password works for login
   - ✅ Customer must change password

### Test via cURL

```bash
# Get customer ID
curl -X GET https://api.samwylock.com/customers \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Resend welcome email
curl -X POST https://api.samwylock.com/customers/CUSTOMER_ID/resend-welcome \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Test Customer Login

```bash
# Try to login with new temporary password
curl -X POST https://api.samwylock.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "customer@example.com",
    "password": "xY9$nMz2!pQ8wE5t"
  }'

# Should get password change challenge
# Use complete-new-password endpoint to set new password
```

## Limitations

### Email Deliverability
- Emails sent from `no-reply@verificationemail.com`
- May end up in spam
- **Solution:** Migrate to SES for better deliverability

### Rate Limits
- Cognito default: 50 emails/day per user pool
- **Solution:** Upgrade to SES for higher limits

### Email Template
- Uses same template as initial welcome email
- Cannot customize per-resend
- **Solution:** Migrate to SES for custom templates

## Future Enhancements

### 1. Email with Custom Message
Add optional message parameter:
```bash
POST /customers/{customer_id}/resend-welcome
{
  "custom_message": "Your admin has reset your password. Please check your email."
}
```

### 2. Notification to Admin
Send email to admin when password is reset:
```
"Password reset for customer@example.com by admin@hovver.com"
```

### 3. Audit Log Endpoint
Track all password resets:
```bash
GET /customers/{customer_id}/password-history
```

### 4. Automatic Expiry Notifications
Email customer 1 day before password expires:
```
"Your temporary password expires in 24 hours. Please login soon!"
```

## Postman Collection

The Postman collection has been updated with:

- **New Request:** "Resend Welcome Email"
- **Tests:** Validates response and password
- **Console Log:** Displays new password
- **Description:** Full use case documentation

**Location:** Customer Management (Admin Only) → Resend Welcome Email

## Summary

✅ **Endpoint Added:** `POST /customers/{customer_id}/resend-welcome`
✅ **Admin Only:** Requires authentication
✅ **New Password:** Auto-generated (16 chars)
✅ **Email Sent:** Automatic via Cognito
✅ **Backup Password:** Returned in API response
✅ **Postman Updated:** New request added
✅ **Documented:** Complete documentation

**Use this endpoint whenever a customer needs their password reset or welcome email resent!**

---

**Files Modified:**
- `api/services/auth.py` - Added `resend_customer_welcome()` method
- `api/models/__init__.py` - Added `ResendWelcomeResponse` model
- `api/routers/customers.py` - Added endpoint
- `Hovver-Admin-Dashboard.postman_collection.json` - Added request

**Ready to use!** Deploy and test with your customers.
