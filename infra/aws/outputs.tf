output "alb_dns_name" {
  value = aws_lb.api.dns_name
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "secrets_manager_arn" {
  value = aws_secretsmanager_secret.app.arn
}

output "rds_endpoint" {
  value = aws_db_instance.postgres.address
}

output "redis_endpoint" {
  value = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "worm_bucket" {
  value = aws_s3_bucket.worm.id
}

output "cloudwatch_log_group" {
  value = aws_cloudwatch_log_group.api.name
}

output "cognito_user_pool_id" {
  value = try(aws_cognito_user_pool.bank[0].id, null)
}

output "waf_acl_arn" {
  value = aws_wafv2_web_acl.api.arn
}
