# =============================================================================
# Monitoring & cost alerting
# =============================================================================
#
# SNS topic for operational alerts. Subscribe an email to receive them:
#   aws sns subscribe --topic-arn <arn> --protocol email \
#     --notification-endpoint you@example.com --region us-east-1
# (then confirm via the emailed link).

resource "aws_sns_topic" "alerts" {
  name = "ai-swim-coach-alerts"
}

# Cost guard: alert if Bedrock invocations spike (proxy for runaway AI spend).
resource "aws_cloudwatch_metric_alarm" "bedrock_high_usage" {
  alarm_name          = "ai-swim-coach-bedrock-high-usage"
  alarm_description   = "Bedrock invocations unusually high (cost guard)"
  namespace           = "AWS/Bedrock"
  metric_name         = "Invocations"
  statistic           = "Sum"
  period              = 86400
  evaluation_periods  = 1
  threshold           = 5000
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

# Lambda error-rate alarm — surfaces spikes in 5xx/handler failures.
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "ai-swim-coach-lambda-errors"
  alarm_description   = "Elevated Lambda error count"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 10
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  dimensions = {
    FunctionName = "ai-swim-coach"
  }
  alarm_actions = [aws_sns_topic.alerts.arn]
}
