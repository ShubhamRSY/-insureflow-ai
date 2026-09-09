# Standalone large-file upload bucket for insureflow-ai.
#
# Deliberately separate from ../aws (the full production landing zone —
# VPC/RDS/ECS/ALB/WAF/Cognito). That stack is for actually hosting the app
# in production; this one is just the S3 bucket the app's
# insureflow.storage.object_storage module needs to accept uploads bigger
# than the ~25MB inline cap. Its own state, its own tiny footprint — safe to
# apply on its own regardless of whether/when the full stack ever exists.
#
# Cost: effectively $0 until you actually store large files in it (S3
# storage is ~$0.023/GB/month; no compute, no VPC, no always-on charges).
#
#   terraform init
#   terraform plan
#   terraform apply

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.5"
    }
  }

  # Remote state: without this, the state file lives only on whichever
  # laptop ran `apply` last. Lose that file (or just work from a second
  # machine) and a fresh apply can't recognize the bucket it already
  # created — it tries to make a second one, orphaning the first. This
  # bucket is versioned (see the one-time bootstrap below), so even a bad
  # state write can be rolled back to a prior version.
  #
  # Deliberately NOT managed by this same Terraform config — a backend has
  # to exist before Terraform can point at it, so it's created once by hand:
  #   aws s3api create-bucket --bucket insureflow-tfstate-<account-id> --region us-east-1
  #   aws s3api put-bucket-versioning --bucket insureflow-tfstate-<account-id> --versioning-configuration Status=Enabled
  #   aws s3api put-bucket-encryption --bucket insureflow-tfstate-<account-id> --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
  #   aws s3api put-public-access-block --bucket insureflow-tfstate-<account-id> --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  backend "s3" {
    bucket  = "insureflow-tfstate-074209490350"
    key     = "aws-uploads/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region
}

# S3 bucket names are globally unique across every AWS account on Earth —
# this suffix avoids a naming collision with someone else's bucket.
resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "uploads" {
  bucket = "${var.project_name}-${var.environment}-uploads-${random_id.suffix.hex}"
  tags   = var.tags
}

resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket                  = aws_s3_bucket.uploads.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_cors_configuration" "uploads" {
  # Skip entirely rather than apply an empty AllowedOrigins (S3 rejects
  # that) — uploads simply won't work from a browser until you set
  # cors_allowed_origins in terraform.tfvars.
  count  = length(var.cors_allowed_origins) > 0 ? 1 : 0
  bucket = aws_s3_bucket.uploads.id
  cors_rule {
    allowed_methods = ["PUT", "POST"]
    allowed_origins = var.cors_allowed_origins
    allowed_headers = ["*"]
    max_age_seconds = 3000
  }
}

# Draft bundles that are abandoned (uploaded, never confirmed/run) shouldn't
# accumulate in the bucket forever — this matches no other business rule,
# it's just a hygiene default; tighten or remove per your retention policy.
resource "aws_s3_bucket_lifecycle_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  rule {
    id     = "expire-unconfirmed-draft-uploads"
    status = "Enabled"
    filter {
      prefix = "draft-uploads/"
    }
    expiration {
      days = var.expire_after_days
    }
  }
}

# A minimal, bucket-scoped IAM policy for whatever identity runs the app
# (an IAM user's access key for local/dev, or an EC2/ECS role in a real
# deployment). Deliberately NOT an aws_iam_user/aws_iam_access_key resource
# here — an access key's secret would then live in Terraform state in
# plaintext. Create the identity by hand in the IAM console and attach this
# policy (see the `app_iam_policy_json` output) instead.
data "aws_iam_policy_document" "uploads_rw" {
  statement {
    sid       = "InsureflowUploadsBucketAccess"
    effect    = "Allow"
    actions   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.uploads.arn}/*"]
  }
  statement {
    sid       = "InsureflowUploadsBucketList"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.uploads.arn]
  }
}
