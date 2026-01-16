# Route53 Record for ALB (in admin-legacy account)
# This creates the DNS record pointing api.samwylock.com to the ALB
resource "aws_route53_record" "app" {
  count    = var.domain_name != "" && var.hosted_zone_id != "" ? 1 : 0
  provider = aws.admin_legacy

  zone_id = var.hosted_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}


