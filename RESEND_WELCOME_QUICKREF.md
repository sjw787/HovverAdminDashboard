# Quick Reference: Resend Welcome Email

## Endpoint

```
POST /customers/{customer_id}/resend-welcome
```

**Auth:** Admin only

## Use When

- ❌ Customer didn't get original email
- ⏰ Temporary password expired (7+ days)
- 🔑 Customer lost their password
- 📧 Email went to spam

## ⚠️ Cannot Use If

- ✅ Customer already set their own password
- Use forgot password flow instead

## Request

```bash
curl -X POST https://api.samwylock.com/customers/{customer_id}/resend-welcome \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## Response

```json
{
  "customer_id": "abc123...",
  "email": "customer@example.com",
  "name": "John Doe",
  "temporary_password": "xY9$nMz2!pQ8wE5t",
  "message": "Welcome email resent with new temporary password"
}
```

## What Happens

1. ✅ Checks user hasn't set password yet
2. ✅ New password generated (16 chars)
3. ✅ Email sent to customer automatically
4. ✅ Password valid for 7 days
5. ✅ Must be changed on login

## Error - Password Already Changed

If customer already set their password:

```json
{
  "detail": "Cannot resend welcome email. Customer has already set their own password. Use the forgot password flow instead."
}
```

**Solution:** Use `POST /auth/forgot-password` instead

## Example

```bash
# List customers to get ID
GET /customers

# Resend to specific customer
POST /customers/abc123.../resend-welcome

# Customer receives email
# Customer logs in with new password
# Customer sets permanent password
```

## Postman

**Location:** Customer Management → Resend Welcome Email

---

**See:** `RESEND_WELCOME_EMAIL.md` for complete documentation
