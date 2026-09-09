variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "insureflow"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "cors_allowed_origins" {
  type        = list(string)
  default     = []
  description = "Browser origin(s) allowed to upload directly to this bucket (e.g. [\"https://app.example.com\"] or [\"http://localhost:5173\"] for local dev). Leave empty and uploads simply won't work from a browser yet — set this before you need the feature."
}

variable "expire_after_days" {
  type        = number
  default     = 30
  description = "Auto-delete objects under draft-uploads/ that were never confirmed/processed, after this many days."
}

variable "tags" {
  type    = map(string)
  default = {}
}
