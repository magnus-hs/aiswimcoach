# =============================================================================
# Lambda Function — AI Swim Coach
# Python 3.12 handler orchestrating the upload pipeline
# Requirements: 3.1, 5.1, 6.1
# =============================================================================

resource "aws_lambda_function" "swim_coach" {
  function_name = "ai-swim-coach"
  description   = "AI Swim Coach — processes FIT uploads, invokes Bedrock, persists results"

  # Deployment package — requires a build step: zip -r backend.zip backend/
  filename         = "${path.module}/../backend.zip"
  source_code_hash = fileexists("${path.module}/../backend.zip") ? filebase64sha256("${path.module}/../backend.zip") : null

  runtime     = "python3.12"
  handler     = "handler.handler"
  timeout     = 28
  memory_size = 256

  role = aws_iam_role.lambda_role.arn

  environment {
    variables = {
      S3_BUCKET      = aws_s3_bucket.uploads.id
      DYNAMODB_TABLE = aws_dynamodb_table.coaching_sessions.name
    }
  }
}

# Allow API Gateway to invoke this Lambda function
resource "aws_lambda_permission" "api_gateway_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.swim_coach.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.swim_coach.execution_arn}/*/*"
}
