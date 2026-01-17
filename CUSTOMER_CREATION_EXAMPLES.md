# Customer Creation API - Quick Test

## Test with curl

### Create Customer (Minimal - Email Only)
```bash
curl -X POST http://localhost:8000/customers \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "name": "Test Customer"
  }'
```

### Create Customer with Phone Number
```bash
curl -X POST http://localhost:8000/customers \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@example.com",
    "name": "Jane Smith",
    "phone_number": "+12025551234"
  }'
```

## Expected Response

```json
{
  "customer_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "email": "customer@example.com",
  "name": "Jane Smith",
  "phone_number": "+12025551234",
  "customer_folder": "customers/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "created_date": "2026-01-17T14:30:00.123456",
  "enabled": true,
  "temporary_password": "aB3$xYz9!mN7pQw2"
}
```

## What Changed from Old API

### OLD API (Deprecated)
```json
{
  "email": "customer@example.com",
  "name": "Jane Smith",
  "temporary_password": "MustProvideThis123!",  // ← You had to provide
  "phone_number": "+12025551234"
}
```

### NEW API (Current)
```json
{
  "email": "customer@example.com",        // ← Required
  "name": "Jane Smith",
  "phone_number": "+12025551234"          // ← Optional
}
// temporary_password removed from request
// temporary_password now in response (auto-generated)
```

## Error Cases

### Missing Email
```bash
curl -X POST http://localhost:8000/customers \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test"}'
```

Response:
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "email"],
      "msg": "Field required"
    }
  ]
}
```

### Invalid Phone Number
```bash
curl -X POST http://localhost:8000/customers \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "name": "Test",
    "phone_number": "1234567890"
  }'
```

Response:
```json
{
  "detail": "Phone number must be in E.164 format (e.g., +1234567890)"
}
```

### Duplicate Email
```bash
curl -X POST http://localhost:8000/customers \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "existing@example.com",
    "name": "Duplicate"
  }'
```

Response:
```json
{
  "detail": "A user with this email already exists"
}
```

## Notes

- ✅ Email is **required** and used as username
- ✅ Phone number is **optional** but must be E.164 format if provided
- ✅ Temporary password is **auto-generated** (16 chars, secure)
- ✅ Password is returned in response
- ✅ Customer must change password on first login
- ✅ Admin needs to send the temporary password to the customer

## Next Steps After Creating Customer

1. **Save the temporary password** from the response
2. **Send credentials to customer** via email/message:
   - Username: [customer email]
   - Temporary Password: [from response]
3. **Tell customer** to change password on first login

## Customer Login Flow

1. Customer logs in with temporary password:
   ```
   POST /auth/login
   {
     "username": "customer@example.com",
     "password": "aB3$xYz9!mN7pQw2"
   }
   ```

2. If password is temporary, they get:
   ```json
   {
     "detail": "New password required. Please reset your password."
   }
   ```

3. Customer completes password change:
   ```
   POST /auth/complete-new-password
   {
     "username": "customer@example.com",
     "temporary_password": "aB3$xYz9!mN7pQw2",
     "new_password": "MyNewPassword123!"
   }
   ```

4. Customer receives auth tokens and can now use the system
