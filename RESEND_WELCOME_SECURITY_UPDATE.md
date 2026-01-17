# Resend Welcome Email - Security Update

## Change Summary

Updated the `POST /customers/{customer_id}/resend-welcome` endpoint to **prevent resending welcome emails to customers who have already set their own password**.

## Why This Change?

### Security & User Experience

**Before:** An admin could potentially reset a customer's permanent password without their knowledge or consent by using the resend welcome email endpoint.

**After:** The endpoint now validates the user's status and only allows resending for customers who are still using their temporary password (haven't completed initial login).

### The Problem Scenario

1. Customer creates account, receives temporary password
2. Customer logs in and changes to permanent password: `MySecurePass123!`
3. Customer uses the system for days/weeks with their password
4. Admin accidentally calls resend welcome email
5. **Before:** Customer's password would be reset without their knowledge
6. **After:** API returns error, customer's password stays intact

## How It Works Now

### Status Check

The endpoint now checks the Cognito `UserStatus` field:

```python
user_response = admin_get_user(...)
user_status = user_response.get('UserStatus')

if user_status == 'CONFIRMED':
    raise HTTPException(400, "Customer has already set their own password")
```

### Allowed Statuses

Resend is **ONLY** allowed for these statuses:

✅ **`FORCE_CHANGE_PASSWORD`**
- User has temporary password
- Must change password on next login
- **This is the normal state for newly created customers**

✅ **`RESET_REQUIRED`**
- Password reset is required
- Temporary state

### Blocked Statuses

Resend is **BLOCKED** for these statuses:

❌ **`CONFIRMED`**
- User has set their own permanent password
- Most common blocking case
- **Use forgot password flow instead**

❌ **Other statuses** (UNCONFIRMED, ARCHIVED, COMPROMISED, etc.)

## Error Response

When trying to resend for a user who already changed their password:

```json
{
  "detail": "Cannot resend welcome email. Customer has already set their own password. Use the forgot password flow instead."
}
```

**HTTP Status:** `400 Bad Request`

## What Admins Should Do

### Scenario 1: Customer Never Logged In (Temporary Password)

**Use:** `POST /customers/{customer_id}/resend-welcome` ✅

This works! Customer gets new temporary password.

### Scenario 2: Customer Already Logged In (Set Their Password)

**Don't Use:** `POST /customers/{customer_id}/resend-welcome` ❌

**Instead:** Tell customer to use forgot password:

1. **Customer initiates:**
   ```bash
   POST /auth/forgot-password
   {
     "username": "customer@example.com"
   }
   ```

2. **Customer receives code** via email

3. **Customer resets password:**
   ```bash
   POST /auth/reset-password
   {
     "username": "customer@example.com",
     "confirmation_code": "123456",
     "new_password": "NewSecurePassword123!"
   }
   ```

## How to Tell If Customer Changed Password

### Method 1: Try the Endpoint

Just try calling resend. If it returns 400 with the error message, they've already set their password.

### Method 2: Check User Details (Future Enhancement)

We could add a field to the customer profile response showing their status.

## Timeline Example

### Day 1 - Account Created
```
Status: FORCE_CHANGE_PASSWORD
Resend Welcome: ✅ ALLOWED
```

### Day 2 - Customer Logs In, Changes Password
```
Status: CONFIRMED
Resend Welcome: ❌ BLOCKED
Use: Forgot Password Flow
```

### Day 10 - Customer Forgot Password
```
Status: CONFIRMED (still)
Resend Welcome: ❌ BLOCKED
Use: Forgot Password Flow
```

## Code Changes

### File: `api/services/auth.py`

Added status validation before allowing resend:

```python
# Check user status
user_response = self.client.admin_get_user(
    UserPoolId=self.user_pool_id,
    Username=username
)

user_status = user_response.get('UserStatus')

# Block if user already set their password
if user_status == 'CONFIRMED':
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Cannot resend welcome email. Customer has already set their own password. Use the forgot password flow instead."
    )

# Only allow specific statuses
if user_status not in ['FORCE_CHANGE_PASSWORD', 'RESET_REQUIRED']:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Cannot resend welcome email. User status is {user_status}..."
    )
```

### File: `api/routers/customers.py`

Updated documentation and error responses:

```python
responses={
    400: {"model": ErrorResponse, "description": "Customer already set their own password"},
    # ...other responses
}
```

## Testing

### Test 1: Newly Created Customer (Should Work)

```bash
# Create customer
POST /customers
{
  "email": "newcustomer@example.com",
  "name": "New Customer"
}

# Immediately try resend
POST /customers/{customer_id}/resend-welcome

# Expected: ✅ 200 OK with new password
```

### Test 2: Customer Who Changed Password (Should Fail)

```bash
# Create customer
POST /customers
{
  "email": "testcustomer@example.com",
  "name": "Test Customer"
}

# Customer logs in and changes password
POST /auth/complete-new-password
{
  "username": "testcustomer@example.com",
  "temporary_password": "TempPass123!",
  "new_password": "MyNewPassword123!"
}

# Try to resend welcome
POST /customers/{customer_id}/resend-welcome

# Expected: ❌ 400 Bad Request
# "Cannot resend welcome email. Customer has already set their own password..."
```

## Security Benefits

✅ **Prevents unauthorized password resets** - Can't reset someone's permanent password
✅ **Clear separation of concerns** - Initial setup vs password recovery
✅ **User consent required** - Forgot password requires user initiation
✅ **Protects active users** - Can't disrupt users who are actively using the system
✅ **Audit trail clarity** - Clear distinction between temporary and permanent passwords

## Documentation Updates

Updated files:
- ✅ `RESEND_WELCOME_EMAIL.md` - Added status validation section
- ✅ `RESEND_WELCOME_QUICKREF.md` - Added restriction notice
- ✅ `api/services/auth.py` - Added inline documentation
- ✅ `api/routers/customers.py` - Updated endpoint docs

## Migration Impact

### For Existing Users

No migration needed! This is purely a validation check. It doesn't change how the feature works for valid use cases.

### For Admins

Admins now need to understand:
- Use **resend welcome** for customers who haven't logged in yet
- Use **forgot password** for customers who already set their password
- The system will tell you which one to use (via error message)

## Summary

| Scenario | Customer Status | Use This Endpoint |
|----------|----------------|-------------------|
| Never received welcome email | FORCE_CHANGE_PASSWORD | `POST /resend-welcome` ✅ |
| Temporary password expired | FORCE_CHANGE_PASSWORD | `POST /resend-welcome` ✅ |
| Lost temporary password | FORCE_CHANGE_PASSWORD | `POST /resend-welcome` ✅ |
| Forgot permanent password | CONFIRMED | `POST /auth/forgot-password` ✅ |
| Need to reset active user | CONFIRMED | `POST /auth/forgot-password` ✅ |

---

**Status:** ✅ Implemented and ready to use

**Security:** Enhanced - prevents unauthorized password resets

**User Impact:** Positive - protects users with permanent passwords
