# =============================================================================
# Secrets Manager — JWT signing secret with rotation support
# =============================================================================
#
# The secret value is JSON: {"current": "...", "previous": "..."}.
# Tokens are signed with `current` and verified against both `current` and
# `previous`, allowing zero-downtime rotation:
#   1. Move the existing `current` value to `previous`, set a new `current`.
#   2. Existing tokens keep validating against `previous` until they expire.
#   3. After the token TTL (7 days) elapses, drop `previous`.
#
# The initial value is managed outside Terraform (seeded via CLI from the
# existing JWT_SECRET) so the plaintext secret is never stored in state/VCS.

resource "aws_secretsmanager_secret" "jwt" {
  name        = "ai-swim-coach/jwt"
  description = "JWT signing secret for AI Swim Coach (current/previous rotation)"
}

# The secret VALUE is intentionally not managed here — it is populated and
# rotated out-of-band so plaintext never lands in Terraform state.
# Use: aws secretsmanager put-secret-value --secret-id ai-swim-coach/jwt \
#        --secret-string '{"current":"<new>","previous":"<old>"}'
