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

## Step 3 — Create the Terraform IAM role

The GitHub Actions workflow runs `terraform apply` before it can upload any
files, so it needs an IAM role it can assume via OIDC.  This role must be
created **manually** (Terraform cannot create its own bootstrap role).

### 3a — Write the trust policy

Replace `<account-id>`, `<owner>`, and `<repo>` with your values, then save
the file as `/tmp/terraform-trust-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<account-id>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:<owner>/<repo>:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

### 3b — Write the permissions policy

The role needs to manage the S3 bucket, CloudFront distribution, and the
scoped deploy IAM role that Terraform creates.  Save the following as
`/tmp/terraform-permissions-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3",
      "Effect": "Allow",
      "Action": ["s3:*"],
      "Resource": ["arn:aws:s3:::*"]
    },
    {
      "Sid": "CloudFront",
      "Effect": "Allow",
      "Action": ["cloudfront:*"],
      "Resource": ["*"]
    },
    {
      "Sid": "IAM",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:GetRole",
        "iam:PutRolePolicy",
        "iam:GetRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:ListRolePolicies",
        "iam:ListAttachedRolePolicies",
        "iam:TagRole",
        "iam:UntagRole",
        "iam:ListInstanceProfilesForRole",
        "iam:PassRole"
      ],
      "Resource": ["arn:aws:iam::*:role/*"]
    }
  ]
}
```

### 3c — Create the role

```bash
aws iam create-role \
  --role-name eq-cli-terraform \
  --assume-role-policy-document file:///tmp/terraform-trust-policy.json

aws iam put-role-policy \
  --role-name eq-cli-terraform \
  --policy-name TerraformDeploy \
  --policy-document file:///tmp/terraform-permissions-policy.json
```

Note the `Arn` value from the `create-role` output (format:
`arn:aws:iam::<account-id>:role/eq-cli-terraform`).  You will need it in
Step 6.

---

## Step 4 — Apply Terraform

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

## Step 5 — Upload the static file (first deploy)

```bash
BUCKET=$(terraform -chdir=terraform output -raw bucket_name)

# Sync all files except index.html (long-lived cache)
aws s3 sync src/eq_cli/static/ "s3://$BUCKET/" \
  --delete \
  --exclude "index.html" \
  --cache-control "public,max-age=3600,s-maxage=86400"

# Upload index.html separately so browsers always fetch the latest version
aws s3 cp src/eq_cli/static/index.html "s3://$BUCKET/index.html" \
  --cache-control "no-cache,must-revalidate"
```

The automated workflow also publishes versioned pages under `/versions/` and
retains:

- every release in the current major line
- already-published `/versions/` entries in the current major line
- only the latest release for each previous major line

Example URLs:

- `https://<cloudfront-domain>/versions/v1.0.0/`
- `https://<cloudfront-domain>/versions/index.json`

Then open `https://$(terraform -chdir=terraform output -raw cloudfront_domain)` in your browser.

> **Note:** CloudFront can take a few minutes to fully propagate the first time.

---

## Step 6 — Set up GitHub Actions secrets and variables

In your GitHub repository go to **Settings → Secrets and variables → Actions** and add:

### Secrets

| Secret name | Value |
|-------------|-------|
| `AWS_TERRAFORM_ROLE_ARN` | ARN of the role created in Step 3 (e.g. `arn:aws:iam::<account-id>:role/eq-cli-terraform`) |
| `AWS_DEPLOY_ROLE_ARN` | Value of the `github_deploy_role_arn` Terraform output (from Step 4) |
| `S3_BUCKET_NAME` | Value of the `bucket_name` Terraform output (from Step 4) |

### Variables (not secrets)

| Variable name | Value |
|---------------|-------|
| `AWS_REGION` | e.g. `us-east-1` |
| `CLOUDFRONT_ALIASES_JSON` | JSON list for Terraform `cloudfront_aliases`, e.g. `[]` or `["eq.example.com"]` |
| `GITHUB_REPO` | Repository in `owner/repo` format (used by Terraform IAM OIDC resources), e.g. `acme/eq-cli` |
| `GITHUB_OIDC_PROVIDER_ARN` | ARN of the GitHub OIDC provider in AWS, e.g. `arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com` |

After this, every push to `main` that changes a file under `src/eq_cli/static/`
or `pyproject.toml` will:

1. Assume `AWS_TERRAFORM_ROLE_ARN` and run `terraform apply` (provisioning/updating the S3 bucket and CloudFront distribution).
2. Read bucket/distribution/domain from Terraform outputs.
3. Assume `AWS_DEPLOY_ROLE_ARN`, sync static assets, publish retained
   `/versions/v<version>/` pages, and upload `/versions/index.json`.
4. Invalidate CloudFront.

The deployment workflow also runs automatically after a successful
`Auto Bump Version` workflow run on `main`.

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
| Old version still showing | Hard-refresh your browser first (index.html is deployed with `no-cache`), then if needed run `aws cloudfront create-invalidation --distribution-id <id> --paths "/*"` or trigger the deploy workflow. |
| GitHub Actions: `Missing AWS_TERRAFORM_ROLE_ARN` | Create the Terraform IAM role following Step 3 and add its ARN as the `AWS_TERRAFORM_ROLE_ARN` secret/variable in **Settings → Secrets and variables → Actions**. |
| GitHub Actions: `Error: Could not assume role` | Verify both `AWS_TERRAFORM_ROLE_ARN` and `AWS_DEPLOY_ROLE_ARN` are set correctly.  Confirm the OIDC provider ARN is correct and that `github_repo` in `terraform.tfvars` (and the `GITHUB_REPO` variable) matches your repository exactly. |
| GitHub Actions: `BucketAlreadyOwnedByYou` or `OriginAccessControlAlreadyExists` during `terraform apply` | Re-run the workflow once after updating to the latest `main`. The workflow now auto-imports pre-existing bucket/OAC/distribution resources into Terraform state before `apply`. If the error persists, verify the bucket name and account match your deployment setup. |
