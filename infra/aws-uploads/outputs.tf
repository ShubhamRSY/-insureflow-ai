output "bucket_name" {
  description = "Set this as S3_UPLOADS_BUCKET in the app's environment."
  value       = aws_s3_bucket.uploads.id
}

output "bucket_arn" {
  value = aws_s3_bucket.uploads.arn
}

output "app_iam_policy_json" {
  description = "Attach this to the IAM user/role that runs the app (create it by hand in the IAM console — see main.tf's comment on why it's not provisioned here)."
  value       = data.aws_iam_policy_document.uploads_rw.json
}
