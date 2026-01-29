# Flexible Deployment Guide: ECS or Lambda

This guide explains how to deploy your Hovver Admin Dashboard backend to either AWS ECS Fargate or AWS Lambda.

## Overview

Your infrastructure now supports two deployment modes:
- **ECS (Elastic Container Service)**: Traditional container deployment with Fargate. Best for consistent workloads.
- **Lambda**: Serverless deployment. Best for variable/sporadic workloads with automatic scaling.

Both modes use the same Docker image stored in ECR, share the same infrastructure (VPC, ALB, Cognito, S3), and are deployed through the same Terraform configuration.

## Architecture

### Common Components (Both Modes)
- Application Load Balancer (ALB) with SSL/TLS
- Amazon Cognito User Pool for authentication
- S3 bucket for image storage
- ECR repository for Docker images
- VPC with public/private subnets
- CloudWatch for logging
- Secrets Manager for API keys

### ECS-Specific Components
- ECS Cluster
- ECS Service with Fargate launch type
- Auto-scaling policies (CPU and memory-based)
- ECS Task Definition
- Target Group with IP target type

### Lambda-Specific Components
- Lambda function with container image
- Lambda function URL
- Target Group with Lambda target type
- Lambda execution role with VPC access

## Prerequisites

1. AWS CLI configured with appropriate credentials
2. Terraform installed (>= 1.0)
3. Docker Desktop running
4. PowerShell (for Windows deployment script)

## Deployment Steps

### 1. Choose Your Deployment Mode

Edit `terraform/terraform.tfvars` and set the deployment mode:

```hcl
# For ECS deployment
deployment_mode = "ecs"

# For Lambda deployment
deployment_mode = "lambda"
```

### 2. Configure Mode-Specific Settings

#### For ECS Deployment:
```hcl
deployment_mode = "ecs"
ecs_desired_count = 2    # Number of tasks
app_cpu = 256            # CPU units (256 = 0.25 vCPU)
app_memory = 512         # Memory in MB
```

#### For Lambda Deployment:
```hcl
deployment_mode = "lambda"
lambda_memory = 512      # Memory in MB (128-10240)
lambda_timeout = 30      # Timeout in seconds (max 900)
```

### 3. Deploy Infrastructure with Terraform

```powershell
cd terraform

# Initialize Terraform (first time only)
terraform init

# Plan the deployment
terraform plan

# Apply the changes
terraform apply
```

Terraform will create only the resources needed for your chosen deployment mode.

### 4. Build and Deploy Docker Image

Use the `build_and_push_docker.ps1` script with the `--Mode` parameter:

#### For ECS Deployment:
```powershell
.\build_and_push_docker.ps1 -Profile your-aws-profile -Mode ecs
```

#### For Lambda Deployment:
```powershell
.\build_and_push_docker.ps1 -Profile your-aws-profile -Mode lambda
```

The script will:
1. Build the appropriate Docker image (Dockerfile for ECS, Dockerfile.lambda for Lambda)
2. Push the image to ECR
3. Trigger a deployment to the specified target (ECS service or Lambda function)
4. Monitor the deployment status until completion

## Switching Between Modes

To switch from one deployment mode to another:

1. **Update terraform.tfvars**:
   ```hcl
   deployment_mode = "lambda"  # or "ecs"
   ```

2. **Apply Terraform changes**:
   ```powershell
   cd terraform
   terraform apply
   ```
   
   This will destroy resources from the old mode and create resources for the new mode.

3. **Deploy the application**:
   ```powershell
   .\build_and_push_docker.ps1 -Profile your-aws-profile -Mode lambda
   ```

## Comparison: ECS vs Lambda

### ECS Fargate
**Pros:**
- Predictable performance
- Better for long-running processes
- More control over scaling behavior
- No cold starts
- Better for consistent traffic

**Cons:**
- Higher minimum cost (always running)
- Requires more configuration
- Slower deployment times

**Best for:**
- Production applications with steady traffic
- Applications requiring consistent response times
- Workloads with predictable patterns

### Lambda
**Pros:**
- Pay only for actual usage
- Automatic scaling to zero
- Lower cost for sporadic workloads
- Simpler infrastructure
- Faster deployments

**Cons:**
- Cold start latency (first request)
- 15-minute maximum execution time
- More complex for long-running operations
- Potential throttling under high load

**Best for:**
- Development/testing environments
- Applications with variable/sporadic traffic
- Cost optimization with unpredictable loads
- APIs with occasional usage

## Cost Comparison

### ECS Fargate (2 tasks, 0.25 vCPU, 512MB)
- **Base cost**: ~$15-20/month (running 24/7)
- **Scales up**: Additional cost per task

### Lambda (512MB memory)
- **No requests**: $0
- **Low traffic** (1000 requests/day): ~$1-2/month
- **Medium traffic** (10,000 requests/day): ~$5-10/month
- **High traffic**: Costs increase linearly

## Monitoring and Logs

Both deployment modes log to CloudWatch Logs:

### ECS Logs:
```
/aws/ecs/hovver-admin-app
```

### Lambda Logs:
```
/aws/lambda/hovver-admin-api-dev
```

View logs in AWS Console or using AWS CLI:
```powershell
# ECS logs
aws logs tail /aws/ecs/hovver-admin-app --follow

# Lambda logs
aws logs tail /aws/lambda/hovver-admin-api-dev --follow
```

## Troubleshooting

### ECS Deployment Issues
1. **Tasks not starting**: Check CloudWatch logs for container errors
2. **Health check failures**: Verify the health check endpoint returns 200
3. **Image pull errors**: Ensure VPC has NAT gateway or VPC endpoints for ECR

### Lambda Deployment Issues
1. **Cold starts**: Consider provisioned concurrency (additional cost)
2. **Timeout errors**: Increase `lambda_timeout` in terraform.tfvars
3. **Memory errors**: Increase `lambda_memory` in terraform.tfvars
4. **VPC connectivity**: Verify Lambda has access to VPC endpoints

### Common Issues (Both Modes)
1. **ALB 502 errors**: Check target health in AWS Console
2. **Secrets Manager access**: Verify IAM roles have correct permissions
3. **S3 access denied**: Check bucket policies and IAM roles

## Testing Your Deployment

After deployment, test your API:

```powershell
# Get the API URL from Terraform outputs
cd terraform
terraform output api_url

# Test the health endpoint
curl https://api.samwylock.com/
# or
curl http://hovver-admin-alb-xxxxx.us-east-1.elb.amazonaws.com/
```

## Rollback Procedure

If you need to rollback:

1. **Revert Terraform changes**:
   ```powershell
   cd terraform
   git checkout HEAD -- terraform.tfvars
   terraform apply
   ```

2. **Deploy previous image** (if needed):
   ```powershell
   # ECS
   aws ecs update-service --cluster hovver-admin-cluster --service hovver-admin-service-dev --force-new-deployment

   # Lambda
   aws lambda update-function-code --function-name hovver-admin-api-dev --image-uri <previous-image-uri>
   ```

## Additional Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [Mangum (FastAPI Lambda Adapter)](https://mangum.io/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
