# Optional DNS alias to the ALB. Banks usually already own Route 53 / InfoBlox /
# Cloudflare DNS — pass an existing zone id rather than creating a public zone.

resource "aws_route53_record" "api" {
  count   = var.domain_name != "" && var.route53_zone_id != "" ? 1 : 0
  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "A"
  alias {
    name                   = aws_lb.api.dns_name
    zone_id                = aws_lb.api.zone_id
    evaluate_target_health = true
  }
}

output "desk_url" {
  value = var.domain_name != "" ? "https://${var.domain_name}" : "https://${aws_lb.api.dns_name}"
}
