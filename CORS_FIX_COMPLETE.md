# CORS Issue Fixed - admin.samwylock.com

## ✅ Issue Resolved

The CORS policy error has been fixed by adding `https://admin.samwylock.com` to the allowed origins list.

---

## What Was Changed

### 1. Updated CORS Origins in `terraform/terraform.tfvars`

**Before:**
```hcl
cors_origins = ["https://samwylock.com", "https://www.samwylock.com"]
```

**After:**
```hcl
cors_origins = ["https://samwylock.com", "https://www.samwylock.com", "https://admin.samwylock.com"]
```

### 2. Applied Changes

✅ **ECS Task Definition** - Updated with new CORS configuration  
✅ **S3 Bucket CORS** - Updated to allow frontend access to images  
✅ **Deployment** - New tasks deployed with updated configuration  

---

## Current CORS Configuration

Your API now accepts requests from these origins:
- ✅ `https://samwylock.com`
- ✅ `https://www.samwylock.com`
- ✅ `https://admin.samwylock.com` ⬅️ **NEW**

### Allowed Methods:
- **API Endpoints**: `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`, `HEAD`, `PATCH`
- **S3 Images**: `GET`, `HEAD`

### Allowed Headers:
- All headers (`*`)

### Credentials:
- Cookies and authentication headers are allowed (`allow_credentials: true`)

---

## Testing CORS

### Test from Browser Console (admin.samwylock.com)

```javascript
// Test health endpoint
fetch('https://api.samwylock.com/', {
  method: 'GET',
  credentials: 'include'
})
.then(res => res.json())
.then(data => console.log('Success:', data))
.catch(err => console.error('Error:', err));

// Test login
fetch('https://api.samwylock.com/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  credentials: 'include',
  body: JSON.stringify({
    username: 'sjw787.sw@gmail.com',
    password: 'YOUR_PASSWORD'
  })
})
.then(res => res.json())
.then(data => console.log('Login Success:', data))
.catch(err => console.error('Login Error:', err));
```

### Verify CORS Headers

```powershell
# Check preflight request (OPTIONS)
Invoke-WebRequest -Uri "https://api.samwylock.com/auth/login" `
  -Method OPTIONS `
  -Headers @{
    "Origin" = "https://admin.samwylock.com"
    "Access-Control-Request-Method" = "POST"
    "Access-Control-Request-Headers" = "Content-Type"
  }
```

**Expected Response Headers:**
```
Access-Control-Allow-Origin: https://admin.samwylock.com
Access-Control-Allow-Methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
Access-Control-Allow-Headers: *
Access-Control-Allow-Credentials: true
Access-Control-Max-Age: 600
```

---

## Deployment Status

The new configuration has been deployed. ECS is rolling out the new task definition:

### Check Deployment Progress

```powershell
# Watch ECS service deployment
aws ecs describe-services `
  --cluster hovver-admin-cluster `
  --services hovver-admin-service-dev `
  --region us-east-1 `
  --query "services[0].deployments"
```

**Expected:**
- 1 deployment with `status: PRIMARY` (new tasks)
- Running count should equal desired count

### Wait for Deployment

The deployment typically takes **2-3 minutes** for:
1. New tasks to start
2. Health checks to pass
3. ALB to route traffic to new tasks
4. Old tasks to drain and stop

You can monitor in real-time:
```powershell
# Watch CloudWatch logs
aws logs tail /ecs/hovver-admin-dev --follow --region us-east-1
```

---

## Troubleshooting

### Still Getting CORS Error?

#### 1. **Wait for Deployment**
New ECS tasks need 2-3 minutes to fully deploy. Check:
```powershell
aws ecs describe-services --cluster hovver-admin-cluster --services hovver-admin-service-dev --region us-east-1 --query "services[0].runningCount"
```

#### 2. **Clear Browser Cache**
The browser might have cached the old CORS response:
- Press `Ctrl+Shift+R` (hard refresh)
- Or clear browser cache
- Or open in Incognito/Private mode

#### 3. **Check ALB Health**
Ensure new tasks are healthy:
```powershell
aws elbv2 describe-target-health `
  --target-group-arn $(aws elbv2 describe-target-groups --region us-east-1 --query "TargetGroups[?starts_with(TargetGroupName, 'hovver-admin')].TargetGroupArn" --output text) `
  --region us-east-1
```

Should show `State: healthy` for all targets.

#### 4. **Verify CORS in Response**
Use browser DevTools:
1. Open DevTools (F12)
2. Go to Network tab
3. Make a request to `https://api.samwylock.com/auth/login`
4. Look for `Access-Control-Allow-Origin` header in response

#### 5. **Check Origin Header**
Ensure your frontend is sending the correct origin:
```javascript
// Should automatically include origin
fetch('https://api.samwylock.com/', {
  // Origin: https://admin.samwylock.com (browser adds this)
})
```

### CORS Working for API but Not S3 Images?

S3 bucket CORS was also updated. If images still don't load:

```powershell
# Verify S3 CORS configuration
aws s3api get-bucket-cors --bucket hovver-images-dev --profile default
```

Should show:
```json
{
  "CORSRules": [{
    "AllowedOrigins": [
      "https://samwylock.com",
      "https://www.samwylock.com", 
      "https://admin.samwylock.com"
    ],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"]
  }]
}
```

---

## Adding More Origins (Future)

To add more allowed origins:

### 1. Update `terraform/terraform.tfvars`
```hcl
cors_origins = [
  "https://samwylock.com",
  "https://www.samwylock.com",
  "https://admin.samwylock.com",
  "https://app.samwylock.com",      # Add new origin
  "http://localhost:3000"            # For local development
]
```

### 2. Apply Changes
```powershell
cd terraform
terraform apply
```

This will automatically update:
- ✅ ECS task definition environment variables
- ✅ S3 bucket CORS configuration
- ✅ Deploy new tasks to ECS

---

## Security Notes

### Production Best Practices

1. **✅ Use HTTPS Only** - All origins use HTTPS (except localhost for dev)
2. **✅ Specific Origins** - Not using wildcard `*` for better security
3. **✅ Credentials Enabled** - Allows cookies and auth headers
4. **✅ Limited Methods** - S3 only allows GET/HEAD (read-only)

### Development vs Production

For local development, you can temporarily add:
```hcl
cors_origins = [
  "https://samwylock.com",
  "https://www.samwylock.com",
  "https://admin.samwylock.com",
  "http://localhost:3000",     # Frontend dev server
  "http://localhost:5173"      # Vite dev server
]
```

**Remember to remove localhost origins before production deployment!**

---

## Summary

✅ **CORS Origins Updated**: Added `https://admin.samwylock.com`  
✅ **ECS Tasks Deployed**: New task definition rolled out  
✅ **S3 CORS Updated**: Frontend can access images  
✅ **Ready to Test**: Frontend should work without CORS errors  

### Test It Now!

From your frontend (`https://admin.samwylock.com`):

```javascript
// This should work now!
fetch('https://api.samwylock.com/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({
    username: 'sjw787.sw@gmail.com',
    password: 'YOUR_PASSWORD'
  })
})
.then(res => res.json())
.then(data => console.log('✅ Login successful!', data));
```

**Expected:** No CORS error, successful login response! 🎉

---

## Quick Reference

### API Endpoints
- **Base URL**: `https://api.samwylock.com`
- **Login**: `POST /auth/login`
- **User Info**: `GET /auth/me`
- **Upload Image**: `POST /images/upload`
- **List Images**: `GET /images/list`

### Credentials
- **Username**: `sjw787.sw@gmail.com`
- **Password**: Get from `terraform output -raw admin_password`

### Allowed Origins
- `https://samwylock.com`
- `https://www.samwylock.com`
- `https://admin.samwylock.com`

**Deployment Time**: 2-3 minutes for full rollout

