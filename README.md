# Hovver Admin Dashboard Backend

Admin Dashboard Backend for Commercial Photography Website with AWS Cognito authentication and S3 image management.

## Features

- **AWS Cognito Authentication**: Secure username/password login with JWT tokens
- **S3 Image Storage**: Upload and manage images with date-based organization
- **Image Gallery**: List and preview all uploaded images with presigned URLs
- **RESTful API**: FastAPI-based REST endpoints with OpenAPI documentation
- **Flexible Deployment**: Deploy to either ECS Fargate or AWS Lambda (configurable at deployment time)
- **Infrastructure as Code**: Complete Terraform configuration for all AWS resources
- **Email Integration**: Customer welcome emails via Resend API

## Architecture

```
                              Internet
                                 │
                                 │
┌────────────────────────────────┼────────────────────────────────┐
│                      VPC       │                                │
│                                │                                │
│  ┌─────────────┐     ┌─────────▼──────┐     ┌─────────────┐   │
│  │   Client    │────▶│      ALB       │────▶│ ECS Fargate │   │
│  └─────────────┘     │ (Public Subnet)│     │(Private Sub)│   │
│                      └────────────────┘     └─────────────┘   │
│                                                    │           │
│                                                    │           │
│         ┌──────────────────────┬───────────────────┼────────┐  │
│         │                      │                   │        │  │
│    ┌────▼─────┐         ┌──────▼──────┐     ┌──────▼────┐  │  │
│    │ Cognito  │         │VPC Endpoints│     │CloudWatch │  │  │
│    │User Pool │◀────────│  (Private)  │────▶│   Logs    │  │  │
│    └──────────┘         │             │     └───────────┘  │  │
│                         │ • S3        │                    │  │
│                         │ • ECR       │     ┌──────────┐   │  │
│                         │ • Logs      │────▶│    S3    │   │  │
│                         └─────────────┘     │  Bucket  │   │  │
│                                             └──────────┘   │  │
└────────────────────────────────────────────────────────────┘  │
```

**Key Features:**
- **No NAT Gateway** - Cost-optimized using VPC Endpoints (~$5-9/month savings)
- **Private AWS Connectivity** - All AWS service traffic stays within AWS network
- **High Security** - ECS tasks in private subnets with no internet access
- **High Availability** - Multi-AZ deployment for resilience

## Prerequisites

- Python 3.14+
- uv package manager
- AWS Account with appropriate permissions
- Terraform >= 1.0 (for infrastructure deployment)
- Docker (for containerization)

## Quick Start

### 1. Install Dependencies

```bash
# Install uv if not already installed
pip install uv

# Install project dependencies
uv pip install -r pyproject.toml
```

### 2. Configure Environment

Copy the example environment file and update with your AWS credentials:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
AWS_REGION=us-east-1
COGNITO_USER_POOL_ID=your-pool-id
COGNITO_CLIENT_ID=your-client-id
S3_BUCKET_NAME=your-bucket-name
```

### 3. Deploy Infrastructure with Terraform

```bash
cd terraform

# Copy and configure variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Apply the infrastructure
terraform apply
```

After deployment, Terraform will output the necessary values. Update your `.env` file with these values.

### 4. Build and Push Docker Image

```bash
# Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-east-1

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build the Docker image
docker build -t hovver-admin-app .

# Tag the image
docker tag hovver-admin-app:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/hovver-admin-app:latest

# Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/hovver-admin-app:latest
```

### 5. Run Locally (Development)

```bash
# Run the application
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Access the API documentation at: http://localhost:8000/docs

## API Endpoints

### Health Check
- `GET /` - Health check endpoint

### Authentication
- `POST /auth/login` - Login with username and password
- `GET /auth/me` - Get current user information (requires authentication)

### Image Management
- `POST /images/upload` - Upload an image (requires authentication)
- `GET /images/list` - List all images with presigned URLs (requires authentication)
- `DELETE /images/{key}` - Delete an image (requires authentication)

## API Usage Examples

### Using Postman Collection

A complete Postman collection is available for testing all endpoints:

1. Import the collection: `Hovver-Admin-Dashboard.postman_collection.json`
2. Set the `base_url` variable (default: `http://localhost:8000`)
3. Run the "Login" request to authenticate
4. The access token will be automatically saved and used for subsequent requests

The collection includes:
- ✅ Automatic token management
- ✅ Test scripts for response validation
- ✅ Example requests for all endpoints
- ✅ Collection variables for easy configuration

### 1. Login

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your-password"
  }'
```

Response:
```json
{
  "access_token": "eyJraWQiOiJ...",
  "id_token": "eyJraWQiOiJ...",
  "refresh_token": "eyJjdHkiOiJ...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### 2. Upload Image

```bash
curl -X POST "http://localhost:8000/images/upload" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@/path/to/image.jpg"
```

### 3. List Images

```bash
curl -X GET "http://localhost:8000/images/list" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. Delete Image

```bash
curl -X DELETE "http://localhost:8000/images/2025/01/14/image_20250114_120000.jpg" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region | `us-east-1` |
| `COGNITO_USER_POOL_ID` | Cognito User Pool ID | Required |
| `COGNITO_CLIENT_ID` | Cognito Client ID | Required |
| `S3_BUCKET_NAME` | S3 bucket name | Required |
| `ENVIRONMENT` | Environment name | `development` |
| `CORS_ORIGINS` | Allowed CORS origins | `["http://localhost:3000"]` |
| `MAX_FILE_SIZE` | Max upload size in bytes | `10485760` (10MB) |
| `PRESIGNED_URL_EXPIRATION` | URL expiration in seconds | `3600` (1 hour) |

## Security

- **Authentication**: AWS Cognito with JWT tokens
- **Authorization**: Bearer token required for protected endpoints
- **IAM Roles**: ECS tasks use IAM roles instead of access keys
- **S3 Security**: Bucket has public access blocked, uses presigned URLs
- **Encryption**: S3 objects encrypted at rest with AES256
- **HTTPS**: ALB supports HTTPS (configure SSL certificate separately)

## Project Structure

```
.
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration management
├── api/                   # API package
│   ├── __init__.py       # Package initialization
│   ├── models/           # Pydantic models
│   │   └── __init__.py   # Request/response models
│   ├── routers/          # API route handlers
│   │   ├── __init__.py   # Router exports
│   │   ├── auth.py       # Authentication endpoints
│   │   └── images.py     # Image management endpoints
│   └── services/         # Business logic services
│       ├── __init__.py   # Service exports
│       ├── auth.py       # Cognito authentication service
│       └── s3.py         # S3 image management service
├── assume_role.py         # AWS STS role assumption script
├── quick_assume.py        # Helper to update .env with assumed credentials
├── pyproject.toml         # Python dependencies
├── Dockerfile             # Docker container configuration
├── .env.example           # Example environment variables
├── QUICK_REFERENCE.txt    # Quick reference for role assumption
├── terraform/             # Terraform infrastructure
│   ├── main.tf           # Main Terraform configuration
│   ├── variables.tf      # Input variables
│   ├── outputs.tf        # Output values
│   ├── vpc.tf            # VPC and networking
│   ├── cognito.tf        # Cognito User Pool
│   ├── s3.tf             # S3 bucket
│   ├── ecs.tf            # ECS cluster and service
│   ├── iam.tf            # IAM roles and policies
│   ├── alb.tf            # Application Load Balancer
│   ├── ecr.tf            # ECR repository
│   └── cloudwatch.tf     # CloudWatch logs
└── README.md              # This file
```

## AWS Role Assumption

For enhanced security, this project includes tools to work with temporary AWS credentials via role assumption:

### Quick Usage

```powershell
# Update .env with temporary credentials from assumed role
python quick_assume.py arn:aws:iam::123456789012:role/HovverAdminRole

# Run the application
uvicorn main:app --reload
```

### Available Tools

- **`assume_role.py`** - Generate temporary credentials by assuming an IAM role
- **`quick_assume.py`** - Quick helper that updates your .env file automatically
- **`ASSUME_ROLE_README.md`** - Comprehensive documentation
- **`QUICK_REFERENCE.txt`** - Command quick reference

### Features

- ✅ Generate temporary AWS credentials (15 min - 12 hours)
- ✅ MFA authentication support
- ✅ External ID for cross-account access
- ✅ Multiple output formats (text, JSON, env, PowerShell)
- ✅ Automatic .env file updates
- ✅ Secure credential management

### Examples

```powershell
# Basic role assumption
python assume_role.py arn:aws:iam::123456789012:role/MyRole

# With MFA
python assume_role.py arn:aws:iam::123456789012:role/SecureRole `
  --mfa-serial arn:aws:iam::123456789012:mfa/user --mfa-token 123456

# Set PowerShell environment variables
python assume_role.py arn:aws:iam::123456789012:role/MyRole `
  --format powershell | Invoke-Expression

# Cross-account access
python assume_role.py arn:aws:iam::987654321098:role/CrossAccountRole `
  --external-id my-external-id-123
```

See `ASSUME_ROLE_README.md` for complete documentation.

## Development

### Running Tests

```bash
# Install test dependencies
uv pip install pytest pytest-cov httpx

# Run tests
pytest
```

### Code Formatting

```bash
# Install formatting tools
uv pip install black isort

# Format code
black .
isort .
```

### API Documentation

FastAPI automatically generates interactive API documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Deployment

The application supports **flexible deployment** to either AWS ECS Fargate or AWS Lambda, with the choice made at deployment time.

### Deployment Modes

#### ECS Fargate (Default)
- Traditional container deployment with auto-scaling
- Best for production with steady traffic
- Always-on architecture with no cold starts
- ~$15-20/month base cost

#### AWS Lambda (Serverless)
- Serverless deployment with automatic scaling to zero
- Best for development/testing or variable workloads
- Pay only for actual usage
- $0 when idle, ~$1-10/month for low-medium traffic

### Quick Deployment

```powershell
# 1. Choose deployment mode in terraform/terraform.tfvars
deployment_mode = "ecs"  # or "lambda"

# 2. Apply infrastructure
cd terraform
terraform apply

# 3. Build and deploy
cd ..
.\build_and_push_docker.ps1 -Profile your-aws-profile -Mode ecs  # or -Mode lambda
```

**See Full Documentation:**
- `DEPLOYMENT_MODES.md` - Comprehensive deployment guide with comparisons, troubleshooting, and best practices
- `QUICK_DEPLOY.md` - Quick reference for common deployment commands

### Architecture Components

Both deployment modes share the following infrastructure:

1. **VPC**: Isolated network with public and private subnets
2. **VPC Endpoints**: Private connectivity to AWS services (S3, ECR, CloudWatch, Secrets Manager)
3. **Application Load Balancer**: Routes traffic to compute (ECS or Lambda)
4. **Cognito User Pool**: Manages user authentication
5. **S3 Bucket**: Stores uploaded images
6. **CloudWatch**: Logs and monitoring
7. **ECR**: Container image registry

**Mode-Specific Components:**
- **ECS Mode**: ECS Cluster, Service, Task Definition, Auto Scaling
- **Lambda Mode**: Lambda Function, Function URL, Lambda execution role

### Cost-Optimized Architecture

This deployment uses **VPC Endpoints** instead of NAT Gateways for cost optimization:

- **VPC Endpoints Used:**
  - S3 Gateway Endpoint (FREE)
  - ECR API Interface Endpoint
  - ECR DKR Interface Endpoint
  - CloudWatch Logs Interface Endpoint
  - Secrets Manager Interface Endpoint

- **Benefits:**
  - ~$5-9/month cost savings compared to NAT Gateway
  - Lower latency to AWS services
  - Enhanced security (no internet access required)
  - Higher reliability (no single point of failure)

**Monthly Cost Estimate:** 
- ECS: ~$54-61/month (idle) | Lambda: $0 (idle), ~$1-10/month (low-medium traffic)

See `VPC_ENDPOINTS_MIGRATION.md` for detailed information about the VPC endpoint architecture.

### Switching Between Deployment Modes

Simply change `deployment_mode` in `terraform/terraform.tfvars` and re-run:

```powershell
terraform apply
.\build_and_push_docker.ps1 -Profile your-aws-profile -Mode [ecs|lambda]
```

### Updating the Application

```bash
# Build new Docker image
docker build -t hovver-admin-app .

# Tag with new version
docker tag hovver-admin-app:latest $ECR_REPO:v1.0.1

# Push to ECR
docker push $ECR_REPO:v1.0.1

# Update ECS service (Terraform will handle this)
cd terraform
terraform apply
```

## Monitoring

- **CloudWatch Logs**: Application logs available in CloudWatch
- **ECS Metrics**: CPU, memory, and request metrics
- **ALB Metrics**: Request count, latency, error rates

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify Cognito User Pool ID and Client ID are correct
   - Check that the user exists and is confirmed
   - Ensure token hasn't expired

2. **Upload Failures**
   - Check IAM role has S3 permissions
   - Verify file size is under limit
   - Ensure file type is allowed

3. **Connection Issues**
   - Check security group rules
   - Verify VPC and subnet configuration
   - Ensure ALB health checks are passing

## License

Proprietary - All Rights Reserved

## Support

For issues and questions, please contact the development team.

