# Multi-User Role System - Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLIENT APPLICATIONS                             │
│                     (Admin Dashboard / Customer Portal)                 │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ HTTPS
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Backend                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐       │
│  │  /auth Router    │  │ /customers Router│  │  /images Router  │       │
│  │                  │  │   (Admin Only)   │  │  (Role-Based)    │       │
│  │ • POST /login    │  │ • POST /         │  │ • POST /upload   │       │
│  │ • GET /me        │  │ • GET /          │  │ • GET /list      │       │
│  │ • POST /change-  │  │ • GET /{id}      │  │ • DELETE /{key}  │       │
│  │   password       │  │ • PATCH /{id}    │  │                  │       │
│  └────────┬─────────┘  └────────┬─────────┘  └─────────┬────────┘       │
│           │                     │                      │                │
│           │                     │                      │                │
│  ┌────────▼─────────────────────▼──────────────────────▼─────────┐      │
│  │               Authorization Middleware                        │      │
│  │  • get_current_user()  • require_admin()                      │      │
│  │  • require_customer()  • get_user_role()                      │      │
│  │  • get_customer_id()                                          │      │
│  └────────┬────────────────────────────────────────┬─────────────┘      │
│           │                                        │                    │
│  ┌────────▼──────────┐                   ┌────────▼──────────┐          │
│  │  CognitoAuth      │                   │    S3Service      │          │
│  │  Service          │                   │                   │          │
│  │                   │                   │ • upload_image()  │          │
│  │ • authenticate()  │                   │ • list_images()   │          │
│  │ • verify_token()  │                   │ • list_for_       │          │
│  │ • create_customer │                   │   customer()      │          │
│  │ • list_customers()│                   │ • delete_image()  │          │
│  │ • get_customer()  │                   │                   │          │
│  │ • update_customer │                   │                   │          │
│  └────────┬──────────┘                   └────────┬──────────┘          │
│           │                                        │                    │
└───────────┼────────────────────────────────────────┼────────────────────┘
            │                                        │
            │                                        │
     ┌──────▼──────┐                          ┌──────▼──────┐
     │   Cognito   │                          │     S3      │
     │  User Pool  │                          │   Bucket    │
     ├─────────────┤                          ├─────────────┤
     │             │                          │             │
     │ ┌─────────┐ │                          │ customers/  │
     │ │ Admins  │ │                          │   {id}/     │
     │ │  Group  │ │                          │   └─files   │
     │ └─────────┘ │                          │             │
     │             │                          │ general/    │
     │ ┌─────────┐ │                          │   └─files   │
     │ │Customers│ │                          │             │
     │ │  Group  │ │                          └─────────────┘
     │ └─────────┘ │
     │             │
     │ Custom Attr:│
     │ customer_id │
     └─────────────┘
```

## Request Flow Examples

### Admin Uploads File for Customer

```
1. Admin → POST /images/upload?customer_id=abc123
           Authorization: Bearer {admin_jwt}
           
2. FastAPI → get_current_user(jwt) → verify token
           
3. FastAPI → get_user_role(user) → "admin"
           
4. FastAPI → Check: user_role == "admin" ✓
           
5. S3Service → upload_image(file, customer_id="abc123")
              → Key: "customers/abc123/2026/01/16/file_123.jpg"
              
6. S3 Bucket → Store file with metadata
              
7. Response ← {success: true, key: "...", folder: "customers/abc123"}
```

### Customer Lists Their Files

```
1. Customer → GET /images/list
              Authorization: Bearer {customer_jwt}
              
2. FastAPI → get_current_user(jwt) → verify token
           
3. FastAPI → get_user_role(user) → "customer"
           
4. FastAPI → get_customer_id(user) → "abc123"
           
5. S3Service → list_images_for_customer("abc123")
              → List: "customers/abc123/*" + "general/*"
              
6. S3 Bucket → Return matching objects
              
7. Response ← {count: 25, images: [{key: "...", url: "..."}]}
```

### Customer Tries to Upload (Denied)

```
1. Customer → POST /images/upload
              Authorization: Bearer {customer_jwt}
              
2. FastAPI → get_current_user(jwt) → verify token
           
3. FastAPI → get_user_role(user) → "customer"
           
4. FastAPI → Check: user_role == "admin" ✗
           
5. Response ← 403 Forbidden: "Customers cannot upload files"
```

## Data Models

### User Token Claims (JWT)
```json
{
  "sub": "abc123-def456-ghi789",
  "email": "user@example.com",
  "cognito:username": "user@example.com",
  "cognito:groups": ["Admins"],  // or ["Customers"]
  "custom:customer_id": "abc123-def456-ghi789",
  "token_use": "access"
}
```

### Customer Profile
```json
{
  "customer_id": "abc123-def456-ghi789",
  "email": "customer@example.com",
  "name": "John Doe",
  "phone_number": "+12345678900",
  "customer_folder": "customers/abc123-def456-ghi789",
  "created_date": "2026-01-16T12:00:00",
  "enabled": true
}
```

### File Metadata (S3)
```json
{
  "key": "customers/abc123/2026/01/16/photo_20260116_120000.jpg",
  "size": 2048576,
  "last_modified": "2026-01-16T12:00:00",
  "presigned_url": "https://s3.amazonaws.com/...",
  "content_type": "image/jpeg",
  "metadata": {
    "original_filename": "photo.jpg",
    "upload_date": "2026-01-16T12:00:00",
    "uploaded_by": "admin@example.com",
    "customer_id": "abc123"
  }
}
```

## Permission Matrix

| Action              | Admin | Customer | Unauthenticated |
|---------------------|-------|----------|-----------------|
| Login               | ✅    | ✅       | ✅              |
| Create Customer     | ✅    | ❌       | ❌              |
| List Customers      | ✅    | ❌       | ❌              |
| View Customer Info  | ✅    | ❌       | ❌              |
| Update Customer     | ✅    | ❌       | ❌              |
| Upload File         | ✅    | ❌       | ❌              |
| List All Files      | ✅    | ❌       | ❌              |
| List Own Files      | ✅    | ✅       | ❌              |
| List General Files  | ✅    | ✅       | ❌              |
| Delete File         | ✅    | ❌       | ❌              |
| Download File       | ✅    | ✅*      | ❌              |

\* Customers can only download their own files + general files

