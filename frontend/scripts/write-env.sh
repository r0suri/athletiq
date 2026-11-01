#!/usr/bin/env bash
# Write frontend/.env.local from the deployed CloudFormation stack's outputs.
# Usage (from frontend/): ./scripts/write-env.sh [stack-name]
set -euo pipefail
STACK="${1:-athletiq-dev}"
out() {
  aws cloudformation describe-stacks --stack-name "$STACK" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}
API_URL="$(out ApiUrl)"; POOL_ID="$(out UserPoolId)"; CLIENT_ID="$(out UserPoolClientId)"
for v in "$API_URL" "$POOL_ID" "$CLIENT_ID"; do
  if [[ -z "$v" || "$v" == "None" ]]; then echo "Could not read outputs of stack $STACK" >&2; exit 1; fi
done
cat > .env.local <<ENV
VITE_API_URL=$API_URL
VITE_COGNITO_USER_POOL_ID=$POOL_ID
VITE_COGNITO_CLIENT_ID=$CLIENT_ID
ENV
echo "Wrote .env.local for stack $STACK"
