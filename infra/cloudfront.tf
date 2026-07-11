# =============================================================================
# CloudFront — CDN for profile pictures
# =============================================================================
#
# Serves profile pictures over HTTPS with caching and keeps the S3 bucket name
# hidden. Origin Access Control (OAC) lets CloudFront read from the (private)
# bucket while blocking direct public S3 access.
#
# NOTE: This was provisioned out-of-band via the AWS CLI first (distribution
# EX1QQETV56OL9, domain d26nv3wz2klag9.cloudfront.net). These resources are
# declared here to capture the infrastructure as code; import the existing
# resources into state before `terraform apply` to avoid recreation:
#   terraform import aws_cloudfront_origin_access_control.profile_pics ERKWCUWMJ4UJM
#   terraform import aws_cloudfront_distribution.profile_pics EX1QQETV56OL9

resource "aws_cloudfront_origin_access_control" "profile_pics" {
  name                              = "ai-swim-coach-profile-pics-oac"
  description                       = "OAC for profile pictures bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "profile_pics" {
  enabled     = true
  comment     = "AI Swim Coach profile pictures CDN"
  price_class = "PriceClass_100"

  origin {
    origin_id                = "profile-pics-s3"
    domain_name              = aws_s3_bucket.profile_pictures.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.profile_pics.id
  }

  default_cache_behavior {
    target_origin_id       = "profile-pics-s3"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    # AWS managed "CachingOptimized" policy
    cache_policy_id = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

output "profile_pics_cdn_domain" {
  value = aws_cloudfront_distribution.profile_pics.domain_name
}
