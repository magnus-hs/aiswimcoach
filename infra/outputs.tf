output "api_gateway_url" {
  value       = aws_api_gateway_stage.prod.invoke_url
  description = "API Gateway invoke URL for the /upload endpoint"
}

output "s3_bucket_name" {
  value = aws_s3_bucket.uploads.id
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.coaching_sessions.name
}

output "lambda_function_name" {
  value = aws_lambda_function.swim_coach.function_name
}
