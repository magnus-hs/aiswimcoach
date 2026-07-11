# =============================================================================
# S3 Bucket — Raw FIT File Uploads
# Requirements: 3.1
# =============================================================================

resource "aws_s3_bucket" "uploads" {
  bucket_prefix = "ai-swim-coach-uploads-"

  tags = {
    Name    = "ai-swim-coach-uploads"
    Purpose = "Raw FIT file storage"
  }
}

# Block all public access — files are only accessed by Lambda
resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# =============================================================================
# S3 Bucket — Profile Pictures
# Requirements: hr-zones-user-profile 23.9-23.11
# =============================================================================

resource "aws_s3_bucket" "profile_pictures" {
  bucket_prefix = "ai-swim-coach-profile-pictures-"

  tags = {
    Name    = "ai-swim-coach-profile-pictures"
    Purpose = "User profile picture storage"
  }
}

# Profile pictures are private and served only via CloudFront (OAC).
# Direct public S3 access is fully blocked.
resource "aws_s3_bucket_public_access_block" "profile_pictures" {
  bucket = aws_s3_bucket.profile_pictures.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Bucket policy: allow ONLY the CloudFront distribution (via OAC) to read.
resource "aws_s3_bucket_policy" "profile_pictures_cloudfront" {
  bucket = aws_s3_bucket.profile_pictures.id

  depends_on = [aws_s3_bucket_public_access_block.profile_pictures]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontOAC"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.profile_pictures.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.profile_pics.arn
          }
        }
      }
    ]
  })
}

# CORS configuration for profile picture uploads from web frontend
resource "aws_s3_bucket_cors_configuration" "profile_pictures" {
  bucket = aws_s3_bucket.profile_pictures.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST"]
    allowed_origins = ["*"] # In production, restrict to specific domains
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}
