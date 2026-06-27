# =============================================================================
# API Gateway — AI Swim Coach
# REST API with POST /upload, Lambda proxy integration, CORS, and error responses
# =============================================================================

# --- REST API ---

resource "aws_api_gateway_rest_api" "swim_coach" {
  name        = "ai-swim-coach-api"
  description = "AI Swim Coach file upload API"

  binary_media_types = ["multipart/form-data"]

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# --- /upload resource ---

resource "aws_api_gateway_resource" "upload" {
  rest_api_id = aws_api_gateway_rest_api.swim_coach.id
  parent_id   = aws_api_gateway_rest_api.swim_coach.root_resource_id
  path_part   = "upload"
}

# --- POST method ---

resource "aws_api_gateway_method" "post_upload" {
  rest_api_id   = aws_api_gateway_rest_api.swim_coach.id
  resource_id   = aws_api_gateway_resource.upload.id
  http_method   = "POST"
  authorization = "NONE"
}

# --- Lambda proxy integration (29-second timeout) ---

resource "aws_api_gateway_integration" "post_upload_lambda" {
  rest_api_id             = aws_api_gateway_rest_api.swim_coach.id
  resource_id             = aws_api_gateway_resource.upload.id
  http_method             = aws_api_gateway_method.post_upload.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.swim_coach.invoke_arn
  timeout_milliseconds    = 29000
}

# --- POST method response (for CORS headers) ---

resource "aws_api_gateway_method_response" "post_upload_200" {
  rest_api_id = aws_api_gateway_rest_api.swim_coach.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.post_upload.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# --- OPTIONS method (CORS preflight) ---

resource "aws_api_gateway_method" "options_upload" {
  rest_api_id   = aws_api_gateway_rest_api.swim_coach.id
  resource_id   = aws_api_gateway_resource.upload.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_upload_mock" {
  rest_api_id = aws_api_gateway_rest_api.swim_coach.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.options_upload.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_upload_200" {
  rest_api_id = aws_api_gateway_rest_api.swim_coach.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.options_upload.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_upload_200" {
  rest_api_id = aws_api_gateway_rest_api.swim_coach.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.options_upload.http_method
  status_code = aws_api_gateway_method_response.options_upload_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# --- Gateway Response: REQUEST_TOO_LARGE (HTTP 413) ---

resource "aws_api_gateway_gateway_response" "request_too_large" {
  rest_api_id   = aws_api_gateway_rest_api.swim_coach.id
  response_type = "REQUEST_TOO_LARGE"
  status_code   = "413"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin" = "'*'"
  }

  response_templates = {
    "application/json" = "{\"error\": \"Request payload exceeds the 10 MB limit.\"}"
  }
}

# --- Gateway Response: DEFAULT_4XX (includes 405 Method Not Allowed) ---

resource "aws_api_gateway_gateway_response" "default_4xx" {
  rest_api_id   = aws_api_gateway_rest_api.swim_coach.id
  response_type = "DEFAULT_4XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin" = "'*'"
  }

  response_templates = {
    "application/json" = "{\"error\": \"$context.error.messageString\"}"
  }
}

# --- Gateway Response: DEFAULT_5XX ---

resource "aws_api_gateway_gateway_response" "default_5xx" {
  rest_api_id   = aws_api_gateway_rest_api.swim_coach.id
  response_type = "DEFAULT_5XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin" = "'*'"
  }

  response_templates = {
    "application/json" = "{\"error\": \"An internal error occurred. Please try again.\"}"
  }
}

# --- Deployment ---

resource "aws_api_gateway_deployment" "swim_coach" {
  rest_api_id = aws_api_gateway_rest_api.swim_coach.id

  depends_on = [
    aws_api_gateway_integration.post_upload_lambda,
    aws_api_gateway_integration.options_upload_mock,
    aws_api_gateway_gateway_response.request_too_large,
    aws_api_gateway_gateway_response.default_4xx,
    aws_api_gateway_gateway_response.default_5xx,
  ]

  # Force redeployment when any resource changes
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.upload,
      aws_api_gateway_method.post_upload,
      aws_api_gateway_integration.post_upload_lambda,
      aws_api_gateway_method.options_upload,
      aws_api_gateway_integration.options_upload_mock,
      aws_api_gateway_method_response.options_upload_200,
      aws_api_gateway_integration_response.options_upload_200,
      aws_api_gateway_gateway_response.request_too_large,
      aws_api_gateway_gateway_response.default_4xx,
      aws_api_gateway_gateway_response.default_5xx,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

# --- Stage ---

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.swim_coach.id
  rest_api_id   = aws_api_gateway_rest_api.swim_coach.id
  stage_name    = "prod"
}
