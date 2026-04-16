# ── GitHub Actions OIDC deploy role ───────────────────────────────────────────
# Creates an IAM role that GitHub Actions can assume via OIDC to deploy the
# static site.  Set var.github_repo and var.github_oidc_provider_arn to enable.
# See DEPLOY.md for instructions on creating the OIDC provider.

resource "aws_iam_role" "github_deploy" {
  count = var.github_repo != "" && var.github_oidc_provider_arn != "" ? 1 : 0
  name  = "${replace(var.bucket_name, ".", "-")}-github-deploy"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = var.github_oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          # Allows any ref (branch, tag, PR) in the specified repository.
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:*"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_deploy" {
  count = var.github_repo != "" && var.github_oidc_provider_arn != "" ? 1 : 0
  name  = "deploy"
  role  = aws_iam_role.github_deploy[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "S3Deploy"
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = [aws_s3_bucket.site.arn, "${aws_s3_bucket.site.arn}/*"]
      },
      {
        Sid      = "CloudFrontInvalidate"
        Effect   = "Allow"
        Action   = ["cloudfront:CreateInvalidation"]
        Resource = aws_cloudfront_distribution.site.arn
      }
    ]
  })
}
