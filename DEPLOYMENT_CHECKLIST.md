# Multi-User Role System - Deployment Checklist

## Pre-Deployment Checklist

### 1. Code Review ✅
- [x] All Python files have no syntax errors
- [x] Type hints are properly used
- [x] Authorization middleware is properly implemented
- [x] Role-based access control is enforced
- [x] S3 file organization follows specification
- [x] API endpoints are properly documented

### 2. Terraform Configuration ✅
- [x] Cognito user pool has custom:customer_id attribute
- [x] Admins user group created
- [x] Customers user group created
- [x] IAM policies include admin operations
- [x] Client read/write attributes updated

### 3. API Implementation ✅
- [x] Customer management endpoints created
- [x] Image upload supports customer_id parameter
- [x] Image listing filters by user role
- [x] Delete operations restricted to admins
- [x] Authorization helpers implemented
- [x] Proper error handling and HTTP status codes

## Deployment Steps

### Step 1: Review Configuration
```powershell
# Review Terraform plan
cd terraform
terraform plan

# Check for any unexpected changes
# Verify:
# - Cognito user pool modifications
# - New user groups
# - IAM policy updates
```

### Step 2: Apply Infrastructure Changes
```powershell
cd terraform
terraform apply

# Wait for completion
# Note down:
# - User Pool ID
# - Client ID
# - Any new resource ARNs
```

### Step 3: Create First Admin User
```powershell
# Option A: Using AWS Console
# 1. Go to Cognito User Pools
# 2. Select your user pool
# 3. Create user with email
# 4. Add to "Admins" group

# Option B: Using AWS CLI
aws cognito-idp admin-create-user `
  --user-pool-id YOUR_POOL_ID `
  --username admin@example.com `
  --user-attributes Name=email,Value=admin@example.com Name=name,Value="Admin User" `
  --temporary-password "TempPass123!" `
  --message-action SUPPRESS

aws cognito-idp admin-add-user-to-group `
  --user-pool-id YOUR_POOL_ID `
  --username admin@example.com `
  --group-name Admins
```

### Step 4: Build Docker Image
```powershell
cd C:\Users\Sam\PycharmProjects\HovverAdminDashboard

# Build image
docker build -t hovver-admin-backend:latest .

# Test locally (optional)
docker run -p 8000:8000 --env-file .env hovver-admin-backend:latest
```

### Step 5: Push to ECR
```powershell
# Use your existing script
.\build_and_push_docker.ps1

# Or manually:
# aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ECR_URL
# docker tag hovver-admin-backend:latest YOUR_ECR_URL/hovver-admin-backend:latest
# docker push YOUR_ECR_URL/hovver-admin-backend:latest
```

### Step 6: Deploy to ECS
```powershell
# If using Terraform
cd terraform
terraform apply -target=aws_ecs_service.main

# Or force new deployment via AWS CLI
aws ecs update-service `
  --cluster hovver-admin-cluster `
  --service hovver-admin-service `
  --force-new-deployment
```

### Step 7: Verify Deployment
```powershell
# Check ECS service status
aws ecs describe-services `
  --cluster hovver-admin-cluster `
  --services hovver-admin-service

# Check task logs
aws logs tail /ecs/hovver-admin-dashboard --follow
```

## Post-Deployment Testing

### Test 1: Health Check
```powershell
curl https://your-api-domain.com/
# Expected: {"status":"healthy",...}
```

### Test 2: Admin Login
```powershell
$loginResponse = curl -X POST https://your-api-domain.com/auth/login `
  -H "Content-Type: application/json" `
  -d '{"username":"admin@example.com","password":"YourPassword123!"}'

# Parse token
$token = ($loginResponse | ConvertFrom-Json).access_token
```

### Test 3: Create Customer
```powershell
curl -X POST https://your-api-domain.com/customers `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d '{
    "email":"customer@example.com",
    "name":"Test Customer",
    "temporary_password":"TempPass123!",
    "phone_number":"+12345678900"
  }'

# Expected: Customer profile with customer_id
```

### Test 4: List Customers
```powershell
curl -X GET https://your-api-domain.com/customers `
  -H "Authorization: Bearer $token"

# Expected: List of customers including the one just created
```

### Test 5: Upload File for Customer
```powershell
$customerId = "customer-id-from-step-3"

curl -X POST "https://your-api-domain.com/images/upload?customer_id=$customerId" `
  -H "Authorization: Bearer $token" `
  -F "file=@test-image.jpg"

# Expected: Upload success with key starting with "customers/{customer_id}/"
```

### Test 6: Upload File to General Folder
```powershell
curl -X POST https://your-api-domain.com/images/upload `
  -H "Authorization: Bearer $token" `
  -F "file=@test-image.jpg"

# Expected: Upload success with key starting with "general/"
```

### Test 7: List Images as Admin
```powershell
curl -X GET https://your-api-domain.com/images/list `
  -H "Authorization: Bearer $token"

# Expected: All images including customer and general files
```

### Test 8: Customer Login
```powershell
$customerLogin = curl -X POST https://your-api-domain.com/auth/login `
  -H "Content-Type: application/json" `
  -d '{"username":"customer@example.com","password":"TempPass123!"}'

# Expected: May require password change on first login
# Handle NEW_PASSWORD_REQUIRED challenge if needed
```

### Test 9: List Images as Customer
```powershell
$customerToken = ($customerLogin | ConvertFrom-Json).access_token

curl -X GET https://your-api-domain.com/images/list `
  -H "Authorization: Bearer $customerToken"

# Expected: Only customer's files + general files
# Should NOT include other customers' files
```

### Test 10: Customer Upload Attempt (Should Fail)
```powershell
curl -X POST https://your-api-domain.com/images/upload `
  -H "Authorization: Bearer $customerToken" `
  -F "file=@test-image.jpg"

# Expected: 403 Forbidden - "Customers cannot upload files"
```

### Test 11: Customer Delete Attempt (Should Fail)
```powershell
curl -X DELETE "https://your-api-domain.com/images/some-file-key" `
  -H "Authorization: Bearer $customerToken"

# Expected: 403 Forbidden - Admin access required
```

### Test 12: Check S3 Organization
```powershell
aws s3 ls s3://hovver-images-{env}/ --recursive

# Expected structure:
# customers/{customer-id}/2026/01/16/...
# general/2026/01/16/...
```

## Rollback Procedure (If Needed)

### If Infrastructure Issues
```powershell
cd terraform
terraform plan -destroy -target=aws_cognito_user_group.admins
terraform plan -destroy -target=aws_cognito_user_group.customers
# Review carefully before destroying
```

### If Application Issues
```powershell
# Revert to previous ECS task definition
aws ecs update-service `
  --cluster hovver-admin-cluster `
  --service hovver-admin-service `
  --task-definition hovver-admin-dashboard:PREVIOUS_REVISION

# Or rollback Docker image
docker tag YOUR_ECR_URL/hovver-admin-backend:previous-tag YOUR_ECR_URL/hovver-admin-backend:latest
docker push YOUR_ECR_URL/hovver-admin-backend:latest
```

## Monitoring

### CloudWatch Alarms to Monitor
- [ ] ECS service healthy task count
- [ ] API Gateway 4xx/5xx error rates
- [ ] Cognito authentication failures
- [ ] S3 upload failures
- [ ] Application error logs

### Key Metrics
- User authentication rate
- Customer creation rate
- File upload success rate
- API response times
- Storage usage by customer

## Documentation Updated
- [x] IMPLEMENTATION_NOTES.md - Detailed implementation guide
- [x] IMPLEMENTATION_SUMMARY.md - Quick reference
- [x] ARCHITECTURE_DIAGRAM.md - Visual architecture
- [x] DEPLOYMENT_CHECKLIST.md - This file

## Support Resources
- AWS Cognito Console: https://console.aws.amazon.com/cognito/
- ECS Console: https://console.aws.amazon.com/ecs/
- S3 Console: https://console.aws.amazon.com/s3/
- CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/

## Common Issues and Solutions

### Issue: "Admin operations not permitted"
**Solution**: Verify IAM role has admin permissions in terraform/iam.tf

### Issue: "Customer_id attribute not found"
**Solution**: Terraform apply may need to recreate user pool. Export/import users if needed.

### Issue: "403 Forbidden even for admin"
**Solution**: Verify user is in Admins group via Cognito console

### Issue: "Files appearing in wrong folders"
**Solution**: Check customer_id parameter in upload requests

### Issue: "Presigned URLs not working"
**Solution**: Verify S3 bucket policy and CORS configuration

## Sign-Off

- [ ] Infrastructure deployed successfully
- [ ] Admin user created and tested
- [ ] Customer creation tested
- [ ] File upload to customer folder tested
- [ ] File upload to general folder tested
- [ ] Customer login tested
- [ ] Role-based file listing verified
- [ ] Authorization rules enforced
- [ ] S3 organization correct
- [ ] CloudWatch monitoring configured
- [ ] Team trained on new features
- [ ] Documentation updated

**Deployed by**: _________________  
**Date**: _________________  
**Environment**: ☐ Development ☐ Staging ☐ Production  
**Version**: _________________

