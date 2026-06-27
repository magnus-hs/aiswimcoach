# -----------------------------------------------------------------------------
# AWS Amplify Hosting for the React Frontend
# Requirements: 8.1, 8.2
# -----------------------------------------------------------------------------

variable "repository_url" {
  description = "Git repository URL for the frontend source code"
  type        = string
}

resource "aws_amplify_app" "ai_swim_coach" {
  name       = "ai-swim-coach"
  repository = var.repository_url

  build_spec = <<-YAML
    version: 1
    frontend:
      phases:
        preBuild:
          commands:
            - cd frontend
            - npm install
        build:
          commands:
            - npm run build
      artifacts:
        baseDirectory: frontend/dist
        files:
          - '**/*'
      cache:
        paths:
          - frontend/node_modules/**/*
  YAML

  environment_variables = {
    VITE_API_ENDPOINT = aws_api_gateway_stage.prod.invoke_url
  }

  depends_on = [aws_api_gateway_stage.prod]
}

resource "aws_amplify_branch" "main" {
  app_id      = aws_amplify_app.ai_swim_coach.id
  branch_name = "main"
}
