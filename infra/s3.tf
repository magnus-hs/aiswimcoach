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
