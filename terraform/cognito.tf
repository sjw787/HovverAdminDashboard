# Cognito User Pool
resource "aws_cognito_user_pool" "main" {
  name = "${var.project_name}-user-pool"

  # Allow users to sign in with username
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  # Password policy
  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 7
  }

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Schema attributes
  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  # Email configuration
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # User pool add-ons
  user_pool_add_ons {
    advanced_security_mode = "ENFORCED"
  }

  tags = {
    Name = "${var.project_name}-user-pool"
  }
}

# Cognito User Pool Client
resource "aws_cognito_user_pool_client" "main" {
  name         = "${var.project_name}-client"
  user_pool_id = aws_cognito_user_pool.main.id

  # Authentication flows
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]

  # Token validity
  access_token_validity  = 1  # 1 hour
  id_token_validity      = 1  # 1 hour
  refresh_token_validity = 30 # 30 days

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  # Don't generate a client secret (for public clients)
  generate_secret = false

  # Prevent user existence errors
  prevent_user_existence_errors = "ENABLED"

  # Read and write attributes
  read_attributes = [
    "email",
    "email_verified"
  ]

  write_attributes = [
    "email"
  ]
}

# Create admin user
resource "aws_cognito_user" "admin" {
  user_pool_id = aws_cognito_user_pool.main.id
  username     = var.admin_username

  attributes = {
    email          = var.admin_email
    email_verified = true
  }

  # Set a temporary password initially
  temporary_password = random_password.admin_password.result

  # Don't send email, we'll set permanent password immediately
  message_action = "SUPPRESS"
}

# Generate password for admin
resource "random_password" "admin_password" {
  length  = 16
  special = true
  upper   = true
  lower   = true
  numeric = true
}

# Set permanent password for admin user using AWS provider
resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${var.project_name}-${random_string.domain_suffix.result}"
  user_pool_id = aws_cognito_user_pool.main.id
}

resource "random_string" "domain_suffix" {
  length  = 8
  special = false
  upper   = false
}

# Use AWS CLI through local-exec with proper error handling
resource "null_resource" "set_admin_password" {
  depends_on = [aws_cognito_user.admin]

  provisioner "local-exec" {
    command     = "aws cognito-idp admin-set-user-password --user-pool-id ${aws_cognito_user_pool.main.id} --username ${var.admin_username} --password \"${random_password.admin_password.result}\" --permanent --region ${var.aws_region}"
    interpreter = ["PowerShell", "-Command"]
  }

  triggers = {
    password    = random_password.admin_password.result
    user_pool   = aws_cognito_user_pool.main.id
    username    = var.admin_username
    always_run  = timestamp()
  }
}


# Output the admin password
output "admin_password" {
  description = "Admin user password for login"
  value       = random_password.admin_password.result
  sensitive   = true
}

