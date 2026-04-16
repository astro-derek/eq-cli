variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "eu-north-1"
}

variable "bucket_name" {
  description = "Globally unique S3 bucket name for the static site (e.g. 'eq-cli-web-yourname')."
  type        = string
}

variable "price_class" {
  description = "CloudFront price class. PriceClass_100 covers North America and Europe only (cheapest). Use PriceClass_All for global coverage."
  type        = string
  default     = "PriceClass_100"

  validation {
    condition     = contains(["PriceClass_100", "PriceClass_200", "PriceClass_All"], var.price_class)
    error_message = "price_class must be one of: PriceClass_100, PriceClass_200, PriceClass_All."
  }
}

variable "github_repo" {
  description = "GitHub repository in 'owner/repo' format used to scope the OIDC deploy role (e.g. 'acme/eq-cli'). Leave empty to skip IAM role creation."
  type        = string
  default     = ""
}

variable "github_oidc_provider_arn" {
  description = "ARN of the GitHub Actions OIDC provider already registered in your AWS account. Required when github_repo is set. See DEPLOY.md for setup instructions."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Map of tags applied to all resources."
  type        = map(string)
  default = {
    Project   = "eq-cli"
    ManagedBy = "Terraform"
  }
}
