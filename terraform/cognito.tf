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

  # Custom attribute for customer_id
  schema {
    name                = "customer_id"
    attribute_data_type = "String"
    required            = false
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

  # Admin create user config (for customer creation)
  admin_create_user_config {
    # Allow only admins to create users (not self-service signup)
    allow_admin_create_user_only = true

    # Customize invitation message
    invite_message_template {
      email_subject = "Welcome to Hover - Your Account Has Been Created"
      email_message = "Hello {username},\n\nYour Hover account has been created!\n\nUsername: {username}\nTemporary Password: {####}\n\nPlease log in and change your password on first login.\n\nBest regards,\nHover Team"
      sms_message   = "Your Hover username is {username} and temporary password is {####}"
    }
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
    "email_verified",
    "name",
    "phone_number",
    "phone_number_verified",
    "custom:customer_id"
  ]

  write_attributes = [
    "email",
    "name",
    "phone_number",
    "custom:customer_id"
  ]
}

# Cognito User Pool Domain
resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${var.project_name}-${random_string.domain_suffix.result}"
  user_pool_id = aws_cognito_user_pool.main.id
}

resource "random_string" "domain_suffix" {
  length  = 8
  special = false
  upper   = false
}

# Cognito User Group - Admins
resource "aws_cognito_user_group" "admins" {
  name         = "Admins"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Administrator users with full access to manage customers and files"
  precedence   = 1
}

# Cognito User Group - Customers
resource "aws_cognito_user_group" "customers" {
  name         = "Customers"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Customer users with access to their own files and general files"
  precedence   = 2
}

