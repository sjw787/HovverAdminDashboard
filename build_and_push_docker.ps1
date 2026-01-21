param(
    [string]$Profile = ""
)

# Build AWS CLI profile argument
$ProfileArg = ""
if ($Profile -ne "") {
    $ProfileArg = "--profile $Profile"
    Write-Host "Using AWS Profile: $Profile" -ForegroundColor Cyan
}

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

# Get AWS Account ID using the specified profile
$getCallerCmd = "aws sts get-caller-identity --query Account --output text $ProfileArg"
$AWS_ACCOUNT_ID = (Invoke-Expression $getCallerCmd).Trim()

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to get AWS account ID. Check your AWS credentials/profile." -ForegroundColor Red
    exit 1
}

$AWS_REGION = "us-east-1"
Write-Host "AWS Account ID: $AWS_ACCOUNT_ID" -ForegroundColor Green
Write-Host "AWS Region: $AWS_REGION" -ForegroundColor Green

# Login to ECR
Write-Host "Logging in to AWS ECR..." -ForegroundColor Cyan
$getPasswordCmd = "aws ecr get-login-password --region $AWS_REGION $ProfileArg"
$password = (Invoke-Expression $getPasswordCmd)
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

# Trigger ECS deployment
Write-Host "`nTriggering ECS deployment..." -ForegroundColor Cyan
$CLUSTER_NAME = "hovver-admin-cluster"
$SERVICE_NAME = "hovver-admin-service-dev"

# Force a new deployment which will pull the latest image from ECR
$updateServiceCmd = "aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force-new-deployment --region $AWS_REGION $ProfileArg"
Invoke-Expression $updateServiceCmd > $null

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to trigger ECS deployment" -ForegroundColor Red
    exit 1
}

Write-Host "ECS deployment triggered successfully!" -ForegroundColor Green
Write-Host "`nMonitoring deployment status..." -ForegroundColor Cyan

# Wait for deployment to complete
$maxWaitSeconds = 600  # 10 minutes timeout
$startTime = Get-Date

while ($true) {
    $elapsedSeconds = ((Get-Date) - $startTime).TotalSeconds

    if ($elapsedSeconds -gt $maxWaitSeconds) {
        Write-Host "WARNING: Deployment monitoring timed out after $maxWaitSeconds seconds." -ForegroundColor Yellow
        Write-Host "The deployment is still in progress. Check AWS console for status." -ForegroundColor Yellow
        break
    }

    # Get service details
    $describeCmd = "aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION $ProfileArg"
    $serviceInfo = (Invoke-Expression $describeCmd) | ConvertFrom-Json

    if ($serviceInfo.services.Count -eq 0) {
        Write-Host "ERROR: Service not found" -ForegroundColor Red
        exit 1
    }

    $service = $serviceInfo.services[0]
    $runningCount = $service.runningCount
    $desiredCount = $service.desiredCount
    $deployments = $service.deployments

    # Check if deployment is complete (only one deployment and running count matches desired)
    if ($deployments.Count -eq 1 -and $runningCount -eq $desiredCount) {
        Write-Host "`nDeployment completed successfully!" -ForegroundColor Green
        Write-Host "Running tasks: $runningCount/$desiredCount" -ForegroundColor Green
        break
    }

    # Show progress
    Write-Host "  Deployments in progress: $($deployments.Count) | Running tasks: $runningCount/$desiredCount" -ForegroundColor Yellow
    Start-Sleep -Seconds 10
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Deployment complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
