# Deploying the eq-cli Static Web App

The `src/eq_cli/static/index.html` page is a fully self-contained, zero-dependency static web application.  It captures audio entirely in the browser via the Web Audio API and stores user settings in `localStorage`.  No Python server is required to run it.

This guide covers deploying it to **AWS S3 + CloudFront** using the Terraform configuration in the `terraform/` directory, plus continuous deployment via GitHub Actions.

---

## Architecture

```
Browser
  └─ CloudFront (HTTPS, global CDN)
       └─ S3 bucket (private, origin-access-control only)
            └─ index.html
```

The S3 bucket is private.  CloudFront is the only entity that can read from it (via Origin Access Control).  All HTTP requests are redirected to HTTPS automatically.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| [Terraform](https://developer.hashicorp.com/terraform/install) | ≥ 1.5 | |
| [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) | any | Must be configured with credentials |
| AWS account | — | IAM permissions to create S3, CloudFront, IAM resources |

---

## Step 1 — Set up the GitHub OIDC provider in AWS

This is a **one-time, per-account** step.  If your AWS account already has the GitHub OIDC provider registered, skip to Step 2.

```bash
aws iam create-open-id-connect-provider \
  --url "https://token.actions.githubusercontent.com" \
  --client-id-list "sts.amazonaws.com" \
  --thumbprint-list \
    "6938fd4d98bab03faadb97b34396831e3780aea1" \
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd"
```

Note the ARN that is printed — you will need it in the next step.

To check if the provider already exists:

```bash
aws iam list-open-id-connect-providers
```

---

## Step 2 — Configure Terraform variables

Copy the example variable file and fill in your values:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # see below
```

Create `terraform/terraform.tfvars` (this file is gitignored):

```hcl
# Required
bucket_name = "eq-cli-web-yourname"   # must be globally unique

# Optional — defaults shown
aws_region  = "us-east-1"
price_class = "PriceClass_100"        # North America + Europe; use PriceClass_All for global

# GitHub Actions OIDC role (skip if you don't want CI/CD)
github_repo              = "your-github-username/eq-cli"
github_oidc_provider_arn = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"

tags = {
  Project   = "eq-cli"
  ManagedBy = "Terraform"
}
```

---

## Step 3 — Apply Terraform

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

After `apply` completes, note the outputs:

| Output | Description |
|--------|-------------|
| `bucket_name` | S3 bucket name |
| `cloudfront_domain` | Public URL (e.g. `d1234abcd.cloudfront.net`) |
| `cloudfront_distribution_id` | ID used for cache invalidations |
| `github_deploy_role_arn` | IAM role ARN for GitHub Actions (empty if OIDC not configured) |

---

## Step 4 — Upload the static file (first deploy)

```bash
aws s3 sync src/eq_cli/static/ s3://$(terraform -chdir=terraform output -raw bucket_name)/ \
  --cache-control "public,max-age=3600,s-maxage=86400"
```

Then open `https://$(terraform -chdir=terraform output -raw cloudfront_domain)` in your browser.

> **Note:** CloudFront can take a few minutes to fully propagate the first time.

---

## Step 5 — Set up GitHub Actions secrets and variables

In your GitHub repository go to **Settings → Secrets and variables → Actions** and add:

### Secrets

| Secret name | Value |
|-------------|-------|
| `AWS_DEPLOY_ROLE_ARN` | Value of the `github_deploy_role_arn` Terraform output |
| `S3_BUCKET_NAME` | Value of the `bucket_name` Terraform output |
| `CLOUDFRONT_DISTRIBUTION_ID` | Value of the `cloudfront_distribution_id` Terraform output |

### Variables (not secrets)

| Variable name | Value |
|---------------|-------|
| `AWS_REGION` | e.g. `us-east-1` |
| `CLOUDFRONT_DOMAIN` | Value of the `cloudfront_domain` Terraform output |

After this, every push to `main` that changes a file under `src/eq_cli/static/` will automatically sync to S3 and invalidate the CloudFront cache via the `.github/workflows/deploy-static.yml` workflow.

You can also trigger a manual deployment from **Actions → Deploy Static Site → Run workflow**.

---

## Optional — Custom domain

To serve the site from your own domain (e.g. `eq.example.com`):

1. **Request an ACM certificate** in `us-east-1` for your domain.
2. Add an `aliases` block and update the `viewer_certificate` in `terraform/main.tf` (see the comments in that file).
3. In your DNS provider, add a `CNAME` record pointing your domain to the CloudFront domain name.
4. Re-run `terraform apply`.

---

## Browser settings persistence

The web app stores all display settings (colors, dB range, band count, etc.) in `localStorage` under the key `eq-cli-settings`.  Click the **⚙ Settings** button in the toolbar to open the settings panel.  Settings survive page refreshes and browser restarts.

To reset to defaults, open the settings panel and click **Reset Defaults**.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `403 Forbidden` from CloudFront | Wait a few minutes after first deploy; S3 bucket policy propagates asynchronously. |
| Old version still showing | CloudFront cache. Run `aws cloudfront create-invalidation --distribution-id <id> --paths "/*"` or trigger the deploy workflow. |
| GitHub Actions: `Error: Could not assume role` | Verify `AWS_DEPLOY_ROLE_ARN`, the OIDC provider ARN, and that `github_repo` in `terraform.tfvars` matches your repository exactly. |
