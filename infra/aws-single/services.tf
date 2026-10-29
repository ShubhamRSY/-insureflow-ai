# AWS services around the single server: S3 (models, uploads, backups, audit trail),
# ECR + SageMaker Serverless (ML predictions), Secrets Manager, CloudWatch logs and
# alarms, SNS email alerts, Budgets, GuardDuty, CloudTrail, and an instance role so
# the server needs no stored keys and is reached through Systems Manager, not SSH.

variable "alert_email" {
  description = "Email for alarms and budget alerts (AWS sends a confirm link first)"
}

variable "monthly_budget_usd" {
  default = 20
}

variable "ml_image" {
  description = "ECR image URI for the SageMaker container; empty until deploy.sh has pushed one"
  default     = ""
}

variable "ml_model_data" {
  description = "s3:// URI of model.tar.gz; empty until deploy.sh has uploaded the models"
  default     = ""
}

data "aws_caller_identity" "me" {}

locals {
  account = data.aws_caller_identity.me.account_id
  ml_on   = var.ml_image != "" && var.ml_model_data != ""
  # SageMaker models are immutable: a new image or model file means a new model name.
  ml_tag = substr(sha1("${var.ml_image}|${var.ml_model_data}"), 0, 8)
}

# ── S3 ───────────────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "data" {
  bucket = "rytera-single-${local.account}"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Browser uploads go straight to S3 with a presigned POST from the app.
resource "aws_s3_bucket_cors_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  cors_rule {
    allowed_methods = ["PUT", "POST"]
    allowed_origins = ["https://${replace(aws_eip.app.public_ip, ".", "-")}.sslip.io"]
    allowed_headers = ["*"]
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    id     = "backups-30-days"
    status = "Enabled"
    filter {
      prefix = "backups/"
    }
    expiration {
      days = 30
    }
    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }
  rule {
    id     = "deploy-bundles-14-days"
    status = "Enabled"
    filter {
      prefix = "deploy/"
    }
    expiration {
      days = 14
    }
  }
  rule {
    id     = "draft-uploads-30-days"
    status = "Enabled"
    filter {
      prefix = "draft-uploads/"
    }
    expiration {
      days = 30
    }
  }
  rule {
    id     = "audit-trail-1-year"
    status = "Enabled"
    filter {
      prefix = "cloudtrail/"
    }
    expiration {
      days = 365
    }
  }
  rule {
    id     = "old-versions-30-days"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

resource "aws_s3_bucket_policy" "data" {
  bucket = aws_s3_bucket.data.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "TlsOnly"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource  = [aws_s3_bucket.data.arn, "${aws_s3_bucket.data.arn}/*"]
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
      {
        Sid       = "CloudTrailAclCheck"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:GetBucketAcl"
        Resource  = aws_s3_bucket.data.arn
      },
      {
        Sid       = "CloudTrailWrite"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.data.arn}/cloudtrail/AWSLogs/${local.account}/*"
        Condition = { StringEquals = { "s3:x-amz-acl" = "bucket-owner-full-control" } }
      },
    ]
  })
}

# ── Secrets Manager: the app's generated secrets, loaded via AWS_SECRETS_ARN ──

resource "aws_secretsmanager_secret" "app" {
  name                    = "rytera-single/app"
  recovery_window_in_days = 7
}

# ── ECR: the SageMaker inference image ──────────────────────────────────────

resource "aws_ecr_repository" "ml" {
  name                 = "rytera-ml"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "ml" {
  repository = aws_ecr_repository.ml.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the last 3 images"
      selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 3 }
      action       = { type = "expire" }
    }]
  })
}

# ── Instance role: no stored keys on the server ─────────────────────────────

resource "aws_iam_role" "ec2" {
  name = "rytera-single-ec2"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "ec2_ssm" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "ec2_app" {
  name = "rytera-app"
  role = aws_iam_role.ec2.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], Resource = "${aws_s3_bucket.data.arn}/*" },
      { Effect = "Allow", Action = ["s3:ListBucket"], Resource = aws_s3_bucket.data.arn },
      { Effect = "Allow", Action = ["secretsmanager:GetSecretValue", "secretsmanager:PutSecretValue"], Resource = aws_secretsmanager_secret.app.arn },
      { Effect = "Allow", Action = ["sagemaker:InvokeEndpoint", "sagemaker:DescribeEndpoint"], Resource = "arn:aws:sagemaker:${var.region}:${local.account}:endpoint/rytera-ml" },
      { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
      {
        Effect   = "Allow"
        Action   = ["ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
        Resource = aws_ecr_repository.ml.arn
      },
      { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogStreams"], Resource = "${aws_cloudwatch_log_group.app.arn}:*" },
    ]
  })
}

resource "aws_iam_instance_profile" "ec2" {
  name = "rytera-single-ec2"
  role = aws_iam_role.ec2.name
}

# ── SageMaker Serverless: pay per prediction, nothing while idle ────────────

resource "aws_iam_role" "sagemaker" {
  name = "rytera-sagemaker"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "sagemaker.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "sagemaker" {
  name = "rytera-sagemaker"
  role = aws_iam_role.sagemaker.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:GetObject"], Resource = "${aws_s3_bucket.data.arn}/models/*" },
      { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
      { Effect = "Allow", Action = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:BatchCheckLayerAvailability"], Resource = aws_ecr_repository.ml.arn },
      { Effect = "Allow", Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], Resource = "arn:aws:logs:${var.region}:${local.account}:log-group:/aws/sagemaker/*" },
      { Effect = "Allow", Action = ["cloudwatch:PutMetricData"], Resource = "*" },
    ]
  })
}

resource "aws_sagemaker_model" "ml" {
  count              = local.ml_on ? 1 : 0
  name               = "rytera-ml-${local.ml_tag}"
  execution_role_arn = aws_iam_role.sagemaker.arn
  primary_container {
    image          = var.ml_image
    model_data_url = var.ml_model_data
  }
}

resource "aws_sagemaker_endpoint_configuration" "ml" {
  count = local.ml_on ? 1 : 0
  name  = "rytera-ml-${local.ml_tag}"
  production_variants {
    variant_name = "all"
    model_name   = aws_sagemaker_model.ml[0].name
    serverless_config {
      memory_size_in_mb = 6144
      max_concurrency   = 2
    }
  }
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_sagemaker_endpoint" "ml" {
  count                = local.ml_on ? 1 : 0
  name                 = "rytera-ml"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.ml[0].name
}

# ── Alerts: SNS email, CloudWatch alarms, Budgets ───────────────────────────

resource "aws_sns_topic" "alerts" {
  name = "rytera-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/rytera/single"
  retention_in_days = 30
}

# Hardware/host failure: AWS moves the server to healthy hardware automatically.
resource "aws_cloudwatch_metric_alarm" "recover" {
  alarm_name          = "rytera-server-host-failure"
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed_System"
  dimensions          = { InstanceId = aws_instance.app.id }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  alarm_actions       = ["arn:aws:automate:${var.region}:ec2:recover", aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "instance_check" {
  alarm_name          = "rytera-server-not-responding"
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed_Instance"
  dimensions          = { InstanceId = aws_instance.app.id }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 3
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  alarm_actions       = ["arn:aws:automate:${var.region}:ec2:reboot", aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "cpu" {
  alarm_name          = "rytera-server-cpu-high"
  namespace           = "AWS/EC2"
  metric_name         = "CPUUtilization"
  dimensions          = { InstanceId = aws_instance.app.id }
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 3
  threshold           = 85
  comparison_operator = "GreaterThanThreshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

# t3 burst credits: when they run out the server slows to ~20% of a CPU.
resource "aws_cloudwatch_metric_alarm" "cpu_credits" {
  alarm_name          = "rytera-server-cpu-credits-low"
  namespace           = "AWS/EC2"
  metric_name         = "CPUCreditBalance"
  dimensions          = { InstanceId = aws_instance.app.id }
  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 2
  threshold           = 20
  comparison_operator = "LessThanThreshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "ml_errors" {
  count               = local.ml_on ? 1 : 0
  alarm_name          = "rytera-ml-endpoint-errors"
  namespace           = "AWS/SageMaker"
  metric_name         = "Invocation5XXErrors"
  dimensions          = { EndpointName = "rytera-ml", VariantName = "all" }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 5
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

resource "aws_budgets_budget" "monthly" {
  name         = "rytera-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  dynamic "notification" {
    for_each = [50, 80, 100]
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = [var.alert_email]
    }
  }
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}

# ── Security: threat detection and an account-wide audit trail ─────────────

resource "aws_guardduty_detector" "main" {
  enable = true
}

resource "aws_cloudtrail" "main" {
  name                          = "rytera-trail"
  s3_bucket_name                = aws_s3_bucket.data.id
  s3_key_prefix                 = "cloudtrail"
  is_multi_region_trail         = true
  include_global_service_events = true
  enable_log_file_validation    = true
  depends_on                    = [aws_s3_bucket_policy.data]
}

output "bucket" {
  value = aws_s3_bucket.data.id
}

output "secret_arn" {
  value = aws_secretsmanager_secret.app.arn
}

output "ecr_repo" {
  value = aws_ecr_repository.ml.repository_url
}

output "instance_id" {
  value = aws_instance.app.id
}
