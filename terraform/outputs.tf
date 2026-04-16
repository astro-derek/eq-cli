output "bucket_name" {
  description = "Name of the S3 bucket holding the static site files."
  value       = aws_s3_bucket.site.id
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain name (e.g. d1234abcd.cloudfront.net). Open this in a browser to view the deployed site."
  value       = aws_cloudfront_distribution.site.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID. Set this as the CLOUDFRONT_DISTRIBUTION_ID GitHub secret."
  value       = aws_cloudfront_distribution.site.id
}

output "github_deploy_role_arn" {
  description = "ARN of the IAM role for GitHub Actions deployments. Set this as the AWS_DEPLOY_ROLE_ARN GitHub secret. Empty when github_repo is not configured."
  value       = var.github_repo != "" ? aws_iam_role.github_deploy[0].arn : ""
}
