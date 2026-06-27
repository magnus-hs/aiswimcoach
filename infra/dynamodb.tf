# =============================================================================
# DynamoDB Table — Coaching Sessions
# Requirements: 6.1
# =============================================================================

resource "aws_dynamodb_table" "coaching_sessions" {
  name         = "coaching-sessions"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "file_key"
  range_key = "created_at"

  attribute {
    name = "file_key"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  tags = {
    Name    = "coaching-sessions"
    Purpose = "Persist coaching responses for auditing"
  }
}
