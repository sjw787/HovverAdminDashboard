# Hovver Admin Dashboard - Terraform Infrastructure

This directory contains Terraform configurations for deploying the Hovver Admin Dashboard infrastructure on AWS.

## Architecture

The infrastructure includes:
- **AWS Cognito User Pool** with an admin user for authentication
- **S3 Bucket** for storing uploaded images with appropriate policies
- **ECS Fargate Cluster** for running the FastAPI application
- **Application Load Balancer** for routing traffic
- **API Gateway** (optional) for additional API management
- **IAM Roles** for secure access between services
- **VPC** with public and private subnets
- **CloudWatch Logs** for application logging
- **ECR Repository** for Docker images

## Prerequisites

- Terraform >= 1.0
- AWS CLI configured with appropriate credentials
- Docker for building application images

## Directory Structure

```
terraform/
├── main.tf              # Main infrastructure configuration
├── variables.tf         # Input variables
├── outputs.tf          # Output values
├── vpc.tf              # VPC and networking
├── cognito.tf          # Cognito User Pool configuration
├── s3.tf               # S3 bucket configuration
├── ecs.tf              # ECS cluster and service
├── iam.tf              # IAM roles and policies
├── alb.tf              # Application Load Balancer
├── ecr.tf              # ECR repository
├── cloudwatch.tf       # CloudWatch logs
└── terraform.tfvars    # Variable values (do not commit sensitive data)
```

## Quick Start

1. Initialize Terraform:
   ```bash
   cd terraform
   terraform init
   ```

2. Review the plan:
   ```bash
   terraform plan
   ```

3. Apply the infrastructure:
   ```bash
   terraform apply
   ```

4. Build and push Docker image:
   ```bash
   # Get ECR login
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
   
   # Build image
   docker build -t hovver-admin-dashboard .
   
   # Tag image
   docker tag hovver-admin-dashboard:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/hovver-admin-dashboard:latest
   
   # Push image
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/hovver-admin-dashboard:latest
   ```

5. Get outputs:
   ```bash
   terraform output
   ```

## Configuration

Copy `terraform.tfvars.example` to `terraform.tfvars` and update with your values:

```hcl
project_name = "hovver-admin"
environment  = "production"
aws_region   = "us-east-1"
admin_email  = "admin@example.com"
```

## Outputs

After applying, Terraform will output:
- Cognito User Pool ID and Client ID
- S3 Bucket Name
- ECS Service URL
- Load Balancer DNS Name
- Admin user credentials (temporary password)

## Clean Up

To destroy all resources:
```bash
terraform destroy
```

**Warning**: This will delete all data including images in S3.

