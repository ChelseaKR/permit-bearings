# Optional AI service for Permit Bearings (ADR 0004) on AWS Lambda.
#
# Shape: one arm64 Lambda behind a Function URL, a DynamoDB table holding the
# per-day request counter (the hard cost ceiling), least-privilege access to
# one Bedrock model, and short log retention. No VPC, no database of
# applicant content, no persistent storage of requests. State is kept
# locally by default (see README.md in this directory).

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "us-west-2"
}

variable "name" {
  type    = string
  default = "permit-bearings-ai"
}

variable "model" {
  description = "Bedrock model or inference-profile ID the service may invoke."
  type        = string
  default     = "global.anthropic.claude-sonnet-4-6"
}

variable "foundation_model" {
  description = "Underlying foundation model ID, for the IAM resource ARN."
  type        = string
  default     = "anthropic.claude-sonnet-4-6"
}

variable "allowed_origins" {
  type    = list(string)
  default = ["https://chelseakr.github.io", "http://localhost:8765", "http://127.0.0.1:8765"]
}

variable "daily_cap" {
  description = "Hard ceiling on model-backed requests per UTC day, all clients combined."
  type        = number
  default     = 100
}

variable "per_client_per_minute" {
  type    = number
  default = 6
}

data "aws_caller_identity" "current" {}

resource "aws_dynamodb_table" "budget" {
  name         = "${var.name}-budget"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "day"

  attribute {
    name = "day"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
}

resource "aws_cloudwatch_log_group" "service" {
  name              = "/aws/lambda/${var.name}"
  retention_in_days = 14
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "service" {
  name               = "${var.name}-role"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

data "aws_iam_policy_document" "service" {
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.service.arn}:*"]
  }
  statement {
    sid     = "InvokeOneModel"
    actions = ["bedrock:InvokeModel"]
    resources = [
      "arn:aws:bedrock:*::foundation-model/${var.foundation_model}",
      "arn:aws:bedrock:*:${data.aws_caller_identity.current.account_id}:inference-profile/${var.model}",
    ]
  }
  statement {
    sid       = "Budget"
    actions   = ["dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.budget.arn]
  }
}

resource "aws_iam_role_policy" "service" {
  name   = "${var.name}-policy"
  role   = aws_iam_role.service.id
  policy = data.aws_iam_policy_document.service.json
}

resource "aws_lambda_function" "service" {
  function_name    = var.name
  role             = aws_iam_role.service.arn
  runtime          = "python3.12"
  architectures    = ["arm64"]
  handler          = "lambda_handler.handler"
  filename         = "${path.module}/package.zip"
  source_code_hash = filebase64sha256("${path.module}/package.zip")
  timeout          = 120
  memory_size      = 1024

  reserved_concurrent_executions = 2

  environment {
    variables = {
      PERMIT_AI_PROVIDER              = "bedrock"
      PERMIT_AI_MODEL                 = var.model
      PERMIT_AI_AWS_REGION            = var.region
      PERMIT_AI_ROOT                  = "/var/task/repo"
      PERMIT_AI_ALLOWED_ORIGINS       = join(",", var.allowed_origins)
      PERMIT_AI_DAILY_CAP             = tostring(var.daily_cap)
      PERMIT_AI_PER_CLIENT_PER_MINUTE = tostring(var.per_client_per_minute)
      PERMIT_AI_BUDGET_TABLE          = aws_dynamodb_table.budget.name
    }
  }

  depends_on = [aws_cloudwatch_log_group.service, aws_iam_role_policy.service]
}

resource "aws_lambda_function_url" "service" {
  function_name      = aws_lambda_function.service.function_name
  authorization_type = "NONE"
  # No CORS block here on purpose: the application's own CORS middleware
  # (PERMIT_AI_ALLOWED_ORIGINS) answers preflights and sets the headers. Two
  # layers would emit Access-Control-Allow-Origin twice, which browsers reject.
}

output "service_url" {
  value = aws_lambda_function_url.service.function_url
}

# A Function URL with authorization_type NONE still requires an explicit
# resource policy before unauthenticated callers are accepted. Since October
# 2025 that is two statements: InvokeFunctionUrl (auth type NONE) and
# InvokeFunction restricted to calls that arrive through the URL.
resource "aws_lambda_permission" "public_url" {
  statement_id           = "AllowPublicFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.service.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

# The AWS provider pinned here has no argument for the InvokedViaFunctionUrl
# condition, so the InvokeFunction statement is added with the CLI (which
# does) and recorded here as a null_resource so `terraform destroy` removes it.
resource "null_resource" "public_url_invoke" {
  triggers = {
    function = aws_lambda_function.service.function_name
    region   = var.region
  }

  provisioner "local-exec" {
    command = <<-EOT
      aws lambda add-permission --region ${var.region} \
        --function-name ${aws_lambda_function.service.function_name} \
        --statement-id AllowPublicFunctionUrlInvoke \
        --action lambda:InvokeFunction --principal '*' --invoked-via-function-url
    EOT
  }

  provisioner "local-exec" {
    when    = destroy
    command = "aws lambda remove-permission --region ${self.triggers.region} --function-name ${self.triggers.function} --statement-id AllowPublicFunctionUrlInvoke || true"
  }
}
