variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "hovver-admin"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "admin_email" {
  description = "Admin user email address"
  type        = string
  default     = "sjw787.sw@gmail.com"
}

variable "admin_username" {
  description = "Admin username for Cognito"
  type        = string
  default     = "sjw787.sw@gmail.com"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones to use"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "app_port" {
  description = "Port the application runs on"
  type        = number
  default     = 8000
}

variable "app_cpu" {
  description = "Fargate CPU units"
  type        = number
  default     = 256
}

variable "app_memory" {
  description = "Fargate memory in MB"
  type        = number
  default     = 512
}

variable "app_count" {
  description = "Number of application instances"
  type        = number
  default     = 2
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the application"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
  default     = 8000
}

variable "cors_origins" {
  description = "CORS allowed origins"
  type        = list(string)
  default     = ["http://localhost:3000"]
}

variable ecs_desired_count {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 2
}

variable "s3_force_destroy" {
  description = "Allow S3 bucket to be destroyed even if it contains objects"
  type        = bool
  default     = false
}

