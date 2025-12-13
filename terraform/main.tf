terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# S3 bucket for dashboard
resource "aws_s3_bucket" "dashboard" {
  bucket = "${var.project_name}-dashboard-${var.environment}"
}

resource "aws_s3_bucket_public_access_block" "dashboard" {
  bucket = aws_s3_bucket.dashboard.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_website_configuration" "dashboard" {
  bucket = aws_s3_bucket.dashboard.id

  index_document {
    suffix = "index.html"
  }
}

resource "aws_s3_bucket_policy" "dashboard" {
  bucket = aws_s3_bucket.dashboard.id

  depends_on = [aws_s3_bucket_public_access_block.dashboard]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.dashboard.arn}/*"
      }
    ]
  })
}

# S3 bucket for raw data storage
resource "aws_s3_bucket" "data" {
  bucket = "${var.project_name}-data-${var.environment}"
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "data" {
  bucket = aws_s3_bucket.data.id

  depends_on = [aws_s3_bucket_public_access_block.data]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.data.arn}/*"
      }
    ]
  })
}

resource "aws_s3_bucket_cors_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    max_age_seconds = 3000
  }
}

# CloudFront distribution
resource "aws_cloudfront_distribution" "dashboard" {
  enabled             = true
  default_root_object = "index.html"

  origin {
    domain_name = aws_s3_bucket.dashboard.bucket_regional_domain_name
    origin_id   = "S3-${aws_s3_bucket.dashboard.id}"
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.dashboard.id}"
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400
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

# DynamoDB table for raw data
resource "aws_dynamodb_table" "raw_data" {
  name         = "${var.project_name}-raw-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "date"
  range_key    = "module"

  attribute {
    name = "date"
    type = "S"
  }

  attribute {
    name = "module"
    type = "S"
  }
}

# DynamoDB table for daily briefs
resource "aws_dynamodb_table" "daily_briefs" {
  name         = "${var.project_name}-briefs-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "date"

  attribute {
    name = "date"
    type = "S"
  }
}

# DynamoDB table for subscribers
resource "aws_dynamodb_table" "subscribers" {
  name         = "${var.project_name}-subscribers-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "email"

  attribute {
    name = "email"
    type = "S"
  }
}

# IAM role for Lambda functions
resource "aws_iam_role" "lambda" {
  name = "${var.project_name}-lambda-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.raw_data.arn,
          aws_dynamodb_table.daily_briefs.arn,
          aws_dynamodb_table.subscribers.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.data.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
      }
    ]
  })
}

# Lambda layer for news fetching
resource "aws_lambda_layer_version" "news_layer" {
  filename   = "layer.zip"
  layer_name = "${var.project_name}-news-layer-${var.environment}"
  compatible_runtimes = ["python3.11"]
}

# Lambda functions
resource "aws_lambda_function" "ingestor_fuel" {
  filename      = "placeholder.zip"
  function_name = "${var.project_name}-ingestor-fuel-${var.environment}"
  role          = aws_iam_role.lambda.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 60
  layers        = [aws_lambda_layer_version.news_layer.arn]

  environment {
    variables = {
      RAW_DATA_TABLE = aws_dynamodb_table.raw_data.name
      EIA_API_KEY    = var.eia_api_key
    }
  }
}

resource "aws_lambda_function" "ingestor_freight" {
  filename      = "placeholder.zip"
  function_name = "${var.project_name}-ingestor-freight-${var.environment}"
  role          = aws_iam_role.lambda.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 60
  layers        = [aws_lambda_layer_version.news_layer.arn]

  environment {
    variables = {
      RAW_DATA_TABLE = aws_dynamodb_table.raw_data.name
    }
  }
}

resource "aws_lambda_function" "ingestor_traffic" {
  filename      = "placeholder.zip"
  function_name = "${var.project_name}-ingestor-traffic-${var.environment}"
  role          = aws_iam_role.lambda.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 60
  layers        = [aws_lambda_layer_version.news_layer.arn]

  environment {
    variables = {
      RAW_DATA_TABLE  = aws_dynamodb_table.raw_data.name
      TRAFFIC_511_KEY = var.traffic_511_key
    }
  }
}

resource "aws_lambda_function" "ingestor_weather" {
  filename      = "placeholder.zip"
  function_name = "${var.project_name}-ingestor-weather-${var.environment}"
  role          = aws_iam_role.lambda.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 60
  layers        = [aws_lambda_layer_version.news_layer.arn]

  environment {
    variables = {
      RAW_DATA_TABLE = aws_dynamodb_table.raw_data.name
    }
  }
}

resource "aws_lambda_function" "aggregator" {
  filename      = "placeholder.zip"
  function_name = "${var.project_name}-aggregator-${var.environment}"
  role          = aws_iam_role.lambda.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 300

  environment {
    variables = {
      RAW_DATA_TABLE    = aws_dynamodb_table.raw_data.name
      BRIEFS_TABLE      = aws_dynamodb_table.daily_briefs.name
      DATA_BUCKET       = aws_s3_bucket.data.id
      OPENAI_API_KEY    = var.openai_api_key
    }
  }
}

resource "aws_lambda_function" "email_sender" {
  filename      = "placeholder.zip"
  function_name = "${var.project_name}-email-sender-${var.environment}"
  role          = aws_iam_role.lambda.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 300

  environment {
    variables = {
      BRIEFS_TABLE      = aws_dynamodb_table.daily_briefs.name
      SUBSCRIBERS_TABLE = aws_dynamodb_table.subscribers.name
      SENDER_EMAIL      = var.sender_email
      DASHBOARD_URL     = "https://${aws_cloudfront_distribution.dashboard.domain_name}"
    }
  }
}

# EventBridge rules
resource "aws_cloudwatch_event_rule" "ingestion" {
  name                = "${var.project_name}-ingestion-${var.environment}"
  description         = "Trigger data ingestion at 5:00 AM ET"
  schedule_expression = "cron(0 10 * * ? *)"
}

resource "aws_cloudwatch_event_rule" "email_delivery" {
  name                = "${var.project_name}-email-${var.environment}"
  description         = "Trigger email delivery at 6:00 AM ET"
  schedule_expression = "cron(0 11 * * ? *)"
}

# EventBridge targets for ingestion
resource "aws_cloudwatch_event_target" "fuel" {
  rule      = aws_cloudwatch_event_rule.ingestion.name
  target_id = "fuel"
  arn       = aws_lambda_function.ingestor_fuel.arn
}

resource "aws_cloudwatch_event_target" "freight" {
  rule      = aws_cloudwatch_event_rule.ingestion.name
  target_id = "freight"
  arn       = aws_lambda_function.ingestor_freight.arn
}

resource "aws_cloudwatch_event_target" "traffic" {
  rule      = aws_cloudwatch_event_rule.ingestion.name
  target_id = "traffic"
  arn       = aws_lambda_function.ingestor_traffic.arn
}

resource "aws_cloudwatch_event_target" "weather" {
  rule      = aws_cloudwatch_event_rule.ingestion.name
  target_id = "weather"
  arn       = aws_lambda_function.ingestor_weather.arn
}

resource "aws_cloudwatch_event_target" "aggregator" {
  rule      = aws_cloudwatch_event_rule.ingestion.name
  target_id = "aggregator"
  arn       = aws_lambda_function.aggregator.arn
}

resource "aws_cloudwatch_event_target" "email" {
  rule      = aws_cloudwatch_event_rule.email_delivery.name
  target_id = "email"
  arn       = aws_lambda_function.email_sender.arn
}

# Lambda permissions for EventBridge
resource "aws_lambda_permission" "fuel" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestor_fuel.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ingestion.arn
}

resource "aws_lambda_permission" "freight" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestor_freight.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ingestion.arn
}

resource "aws_lambda_permission" "traffic" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestor_traffic.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ingestion.arn
}

resource "aws_lambda_permission" "weather" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestor_weather.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ingestion.arn
}

resource "aws_lambda_permission" "aggregator" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.aggregator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ingestion.arn
}

resource "aws_lambda_permission" "email" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.email_sender.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.email_delivery.arn
}
