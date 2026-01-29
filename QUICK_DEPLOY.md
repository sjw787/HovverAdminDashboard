# Quick Deployment Reference

## Deploy to ECS (Default)

```powershell
# 1. Set deployment mode in terraform.tfvars
deployment_mode = "ecs"

# 2. Apply Terraform
cd terraform
terraform apply

# 3. Build and deploy
cd ..
.\build_and_push_docker.ps1 -Profile iamadmin-dev -Mode ecs
```

## Deploy to Lambda

```powershell
# 1. Set deployment mode in terraform.tfvars
deployment_mode = "lambda"

# 2. Apply Terraform
cd terraform
terraform apply

# 3. Build and deploy
cd ..
.\build_and_push_docker.ps1 -Profile iamadmin-dev -Mode lambda
```

## Switch Between Modes

```powershell
# Change deployment_mode in terraform.tfvars, then:
cd terraform
terraform apply
cd ..
.\build_and_push_docker.ps1 -Profile iamadmin-dev -Mode [ecs|lambda]
```

## Quick Commands

```powershell
# View outputs
terraform output

# Check ECS service status
aws ecs describe-services --cluster hovver-admin-cluster --services hovver-admin-service-dev --profile iamadmin-dev

# Check Lambda function status
aws lambda get-function --function-name hovver-admin-api-dev --profile iamadmin-dev

# View logs (ECS)
aws logs tail /aws/ecs/hovver-admin-app --follow --profile iamadmin-dev

# View logs (Lambda)
aws logs tail /aws/lambda/hovver-admin-api-dev --follow --profile iamadmin-dev

# Test API
curl https://api.samwylock.com/
```

## Key Files

- `terraform/terraform.tfvars` - Deployment configuration
- `Dockerfile` - ECS container image
- `Dockerfile.lambda` - Lambda container image
- `lambda_handler.py` - Lambda entry point
- `build_and_push_docker.ps1` - Build and deploy script

## Architecture Files

- `terraform/ecs.tf` - ECS resources (conditional)
- `terraform/lambda.tf` - Lambda resources (conditional)
- `terraform/alb.tf` - ALB (shared by both modes)
- `terraform/iam.tf` - IAM roles (mode-specific)
