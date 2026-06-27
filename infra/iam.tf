# =============================================================================
# IAM — Lambda Execution Role and Permissions
# Requirements: 3.1, 5.1, 6.1
# =============================================================================

# --- Lambda execution role ---

resource "aws_iam_role" "lambda_role" {
  name = "ai-swim-coach-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# --- Inline policy: S3, Bedrock, DynamoDB permissions ---

resource "aws_iam_role_policy" "lambda_permissions" {
  name = "ai-swim-coach-lambda-permissions"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "S3PutObject"
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "${aws_s3_bucket.uploads.arn}/*"
      },
      {
        Sid      = "BedrockInvokeModel"
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel"]
        Resource = [
          "arn:aws:bedrock:*::foundation-model/anthropic.*",
          "arn:aws:bedrock:*:*:inference-profile/us.anthropic.*"
        ]
      },
      {
        Sid      = "MarketplaceSubscription"
        Effect   = "Allow"
        Action   = [
          "aws-marketplace:ViewSubscriptions",
          "aws-marketplace:Subscribe",
          "aws-marketplace:Unsubscribe"
        ]
        Resource = "*"
      },
      {
        Sid      = "DynamoDBPutItem"
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem"]
        Resource = aws_dynamodb_table.coaching_sessions.arn
      }
    ]
  })
}

# --- Managed policy: CloudWatch Logs (basic execution) ---

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
