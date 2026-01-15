# Check if Docker is running
try {
    docker info > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Docker Desktop is not running. Please start Docker Desktop and try again." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "ERROR: Docker Desktop is not running. Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

Write-Host "Docker is running, proceeding with build and push..." -ForegroundColor Green

$AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text).Trim()
$AWS_REGION = "us-east-1"

# Login to ECR
Write-Host "Logging in to AWS ECR..." -ForegroundColor Cyan
$password = (aws ecr get-login-password --region $AWS_REGION)
docker login --username AWS --password $password "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to login to ECR" -ForegroundColor Red
    exit 1
}
Write-Host "ECR login successful!" -ForegroundColor Green

Write-Host "Building Docker image..." -ForegroundColor Cyan
docker build -t hovver-admin-app .

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker build failed" -ForegroundColor Red
    exit 1
}
Write-Host "Docker build successful!" -ForegroundColor Green

Write-Host "Tagging Docker image..." -ForegroundColor Cyan
docker tag hovver-admin-app:latest "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/hovver-admin-app:latest"

Write-Host "Pushing Docker image to ECR..." -ForegroundColor Cyan
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/hovver-admin-app:latest"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker push failed" -ForegroundColor Red
    exit 1
}
Write-Host "Docker push successful! Image is now in ECR." -ForegroundColor Green

