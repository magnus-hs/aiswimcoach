#!/bin/bash
# =============================================================================
# Infrastructure Setup: ai-swim-coach-friends DynamoDB Table
# Requirements: Friends Network - Infrastructure prerequisite for all friend operations
#
# This script creates the DynamoDB table for friend relationships and updates
# the Lambda IAM role with permissions for the new table.
#
# Region: us-east-1
# Account: 562535532900
# =============================================================================

set -euo pipefail

REGION="us-east-1"
TABLE_NAME="ai-swim-coach-friends"
ROLE_NAME="ai-swim-coach-lambda-role"
POLICY_NAME="ai-swim-coach-lambda-permissions"
ACCOUNT_ID="562535532900"

echo "=== Creating DynamoDB table: ${TABLE_NAME} ==="

aws dynamodb create-table \
  --table-name "${TABLE_NAME}" \
  --attribute-definitions \
    AttributeName=pk,AttributeType=S \
    AttributeName=sk,AttributeType=S \
  --key-schema \
    AttributeName=pk,KeyType=HASH \
    AttributeName=sk,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --global-secondary-indexes '[
    {
      "IndexName": "sk-pk-index",
      "KeySchema": [
        {"AttributeName": "sk", "KeyType": "HASH"},
        {"AttributeName": "pk", "KeyType": "RANGE"}
      ],
      "Projection": {"ProjectionType": "ALL"}
    }
  ]' \
  --region "${REGION}"

echo "Waiting for table to become ACTIVE..."
aws dynamodb wait table-exists \
  --table-name "${TABLE_NAME}" \
  --region "${REGION}"

echo "Table ${TABLE_NAME} is ACTIVE."

# =============================================================================
# Update IAM inline policy to add DynamoDB permissions for the friends table
# =============================================================================

echo ""
echo "=== Updating IAM policy: ${POLICY_NAME} on role ${ROLE_NAME} ==="

# Fetch the current inline policy
CURRENT_POLICY=$(aws iam get-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-name "${POLICY_NAME}" \
  --query "PolicyDocument" \
  --output json \
  --region "${REGION}")

# Add the new DynamoDB Friends statement to the existing policy
UPDATED_POLICY=$(echo "${CURRENT_POLICY}" | python3 -c "
import json, sys

policy = json.load(sys.stdin)

# Check if the DynamoDBFriends statement already exists
existing_sids = [s.get('Sid', '') for s in policy['Statement']]
if 'DynamoDBFriends' in existing_sids:
    print('DynamoDBFriends statement already exists, skipping.', file=sys.stderr)
    json.dump(policy, sys.stdout)
    sys.exit(0)

# Add the new statement for the friends table
new_statement = {
    'Sid': 'DynamoDBFriends',
    'Effect': 'Allow',
    'Action': [
        'dynamodb:GetItem',
        'dynamodb:PutItem',
        'dynamodb:DeleteItem',
        'dynamodb:Query'
    ],
    'Resource': [
        'arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/${TABLE_NAME}',
        'arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/${TABLE_NAME}/index/sk-pk-index'
    ]
}

policy['Statement'].append(new_statement)
json.dump(policy, sys.stdout)
")

# Apply the updated policy
aws iam put-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-name "${POLICY_NAME}" \
  --policy-document "${UPDATED_POLICY}" \
  --region "${REGION}"

echo "IAM policy updated successfully with DynamoDBFriends permissions."
echo ""
echo "=== Setup complete ==="
echo "Table: ${TABLE_NAME}"
echo "  Partition Key: pk (String)"
echo "  Sort Key: sk (String)"
echo "  GSI: sk-pk-index (sk → pk)"
echo "  Billing: PAY_PER_REQUEST"
echo "  Region: ${REGION}"
echo ""
echo "IAM permissions added:"
echo "  - dynamodb:GetItem"
echo "  - dynamodb:PutItem"
echo "  - dynamodb:DeleteItem"
echo "  - dynamodb:Query"
echo "  Resources:"
echo "    - arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/${TABLE_NAME}"
echo "    - arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/${TABLE_NAME}/index/sk-pk-index"
