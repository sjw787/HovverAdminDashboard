output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_client_id" {
  description = "Cognito User Pool Client ID"
  value       = aws_cognito_user_pool_client.main.id
}

output "s3_bucket_name" {
  description = "S3 bucket name for images"
  value       = aws_s3_bucket.images.id
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.images.arn
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.app.repository_url
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = aws_lb.main.dns_name
}

output "alb_url" {
  description = "Application URL"
  value       = "http://${aws_lb.main.dns_name}"
}

output "ecs_cluster_name" {
  description = "ECS Cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS Service name"
  value       = aws_ecs_service.app.name
}

output "admin_user_instructions" {
  description = "Instructions for admin user setup"
  value       = <<-EOT
    Admin user '${var.admin_username}' has been created.
    A temporary password has been sent to: ${var.admin_email}

    Please check your email and use the temporary password to log in.
    You will be required to change the password on first login.

    API Endpoint: http://${aws_lb.main.dns_name}

    To set environment variables for your application:
    export COGNITO_USER_POOL_ID="${aws_cognito_user_pool.main.id}"
    export COGNITO_CLIENT_ID="${aws_cognito_user_pool_client.main.id}"
    export S3_BUCKET_NAME="${aws_s3_bucket.images.id}"
    export AWS_REGION="${var.aws_region}"
  EOT
}

output "cloudwatch_log_group" {
  description = "CloudWatch Log Group name"
  value       = aws_cloudwatch_log_group.app.name
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

