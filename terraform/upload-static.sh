#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./upload-static.sh [aws-profile] [-- aws s3 sync args]
# Examples:
#   ./upload-static.sh
#   ./upload-static.sh default
#   ./upload-static.sh default -- --dryrun

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROFILE="default"

if [[ "${1:-}" != "" && "${1:-}" != "--" ]]; then
  PROFILE="$1"
  shift
fi

if [[ "${1:-}" == "--" ]]; then
  shift
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "Error: aws CLI is not installed or not on PATH." >&2
  exit 1
fi

if ! command -v terraform >/dev/null 2>&1; then
  echo "Error: terraform is not installed or not on PATH." >&2
  exit 1
fi

SOURCE_DIR="$REPO_ROOT/src/eq_cli/static/"
if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Error: static directory not found at $SOURCE_DIR" >&2
  exit 1
fi

# Export short-lived AWS credentials from the selected profile.
eval "$(AWS_PAGER='' aws --no-cli-pager configure export-credentials --profile "$PROFILE" --format env)"

BUCKET_NAME="$(terraform -chdir="$SCRIPT_DIR" output -raw bucket_name)"

aws s3 sync "$SOURCE_DIR" "s3://$BUCKET_NAME/" \
  --cache-control "public,max-age=3600,s-maxage=86400" \
  "$@"