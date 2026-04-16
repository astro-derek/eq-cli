#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./tf.sh [aws-profile] <terraform-command> [-- terraform args]
# Examples:
#   ./tf.sh default plan
#   ./tf.sh default apply -- -auto-approve
#   ./tf.sh default destroy -- -auto-approve
#   ./tf.sh default plan -- -no-color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "" ]]; then
  echo "Usage: ./tf.sh [aws-profile] <terraform-command> [-- terraform args]" >&2
  exit 1
fi

PROFILE="$1"
shift

if [[ "${1:-}" == "" ]]; then
  echo "Error: missing terraform command (for example: plan, apply, destroy)." >&2
  exit 1
fi

TF_COMMAND="$1"
shift

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

# Export short-lived AWS credentials from the selected profile.
eval "$(AWS_PAGER='' aws --no-cli-pager configure export-credentials --profile "$PROFILE" --format env)"

terraform -chdir="$SCRIPT_DIR" "$TF_COMMAND" "$@"