# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-logs"
  }
}

# CloudWatch Log Stream
resource "aws_cloudwatch_log_stream" "app" {
  name           = "${var.project_name}-log-stream"
  log_group_name = aws_cloudwatch_log_group.app.name
}

