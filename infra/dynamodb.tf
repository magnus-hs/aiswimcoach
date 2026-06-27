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

# =============================================================================
# DynamoDB Table — Users
# Requirements: hr-zones-user-profile 5.1, 15.1, 23.9
# =============================================================================

resource "aws_dynamodb_table" "users" {
  name         = "ai-swim-coach-users"
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "email"
    type = "S"
  }

  # GSI for email-based lookups during login
  global_secondary_index {
    name            = "email-index"
    hash_key        = "email"
    projection_type = "ALL"
  }

  tags = {
    Name    = "ai-swim-coach-users"
    Purpose = "User authentication and profile picture URLs"
  }
}

# =============================================================================
# DynamoDB Table — UserProfiles
# Requirements: hr-zones-user-profile 5.1-5.6
# =============================================================================

resource "aws_dynamodb_table" "user_profiles" {
  name         = "ai-swim-coach-user-profiles"
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  tags = {
    Name    = "ai-swim-coach-user-profiles"
    Purpose = "User demographic and ability profile data"
  }
}

# =============================================================================
# DynamoDB Table — Sessions
# Requirements: hr-zones-user-profile 15.1-15.12
# =============================================================================

resource "aws_dynamodb_table" "sessions" {
  name         = "ai-swim-coach-sessions"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "user_id"
  range_key = "session_date"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "session_date"
    type = "S"
  }

  attribute {
    name = "session_id"
    type = "S"
  }

  # GSI for session_id-based lookups for detailed session retrieval
  global_secondary_index {
    name            = "session_id-index"
    hash_key        = "session_id"
    projection_type = "ALL"
  }

  tags = {
    Name    = "ai-swim-coach-sessions"
    Purpose = "Historical swim session data with metrics and coaching results"
  }
}
