variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "rytera"
}

variable "environment" {
  type    = string
  default = "production"
}

variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}

variable "allowed_cidr_blocks" {
  type        = list(string)
  description = "CIDRs allowed to hit the ALB (restrict to bank VPN / office)"
  default     = ["0.0.0.0/0"]
}

variable "acm_certificate_arn" {
  type        = string
  description = "ACM cert ARN for HTTPS listener (app.rytera.ai)"
}

variable "container_image" {
  type        = string
  description = "ECR image URI for insureflow API"
  default     = "ghcr.io/example/insureflow-ai:latest"
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.medium"
}

variable "redis_node_type" {
  type    = string
  default = "cache.t4g.micro"
}

variable "ecs_cpu" {
  type    = string
  default = "1024"
}

variable "ecs_memory" {
  type    = string
  default = "2048"
}

variable "ecs_desired_count" {
  type    = number
  default = 2
}

variable "ecs_worker_desired_count" {
  type        = number
  default     = 1
  description = "Celery workers for pipeline/mortgage/agent queues (orchestration bus)."
}

variable "langsmith_api_key" {
  type      = string
  default   = ""
  sensitive = true
}

variable "langsmith_project" {
  type    = string
  default = "insureflow-evals"
}

variable "enable_cognito" {
  type    = bool
  default = true
}

variable "cognito_callback_urls" {
  type    = list(string)
  default = ["https://app.rytera.ai/auth/sso/callback"]
}

variable "domain_name" {
  type        = string
  default     = ""
  description = "FQDN for the desk (e.g. uw.bank.example). Empty = skip Route 53."
}

variable "route53_zone_id" {
  type        = string
  default     = ""
  description = "Existing public hosted zone. Required when domain_name is set."
}

variable "waf_rate_limit" {
  type        = number
  default     = 2000
  description = "WAF requests per 5 minutes per IP before block (DDoS / credential stuffing)."
}

variable "tags" {
  type    = map(string)
  default = {}
}
