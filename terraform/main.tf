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

resource "aws_s3_bucket_server_side_encryption_configuration" "dashboard" {
  bucket = aws_s3_bucket.dashboard.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "dashboard" {
  bucket = aws_s3_bucket.dashboard.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "dashboard" {
  bucket = aws_s3_bucket.dashboard.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_website_configuration" "dashboard" {
  bucket = aws_s3_bucket.dashboard.id

  index_document {
    suffix = "index.html"
  }
}

# Origin Access Control for CloudFront
resource "aws_cloudfront_origin_access_control" "dashboard" {
  name                              = "${var.project_name}-dashboard-oac"
  description                       = "OAC for dashboard S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_s3_bucket_policy" "dashboard" {
  bucket = aws_s3_bucket.dashboard.id

  depends_on = [aws_s3_bucket_public_access_block.dashboard]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontServicePrincipal"
        Effect    = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.dashboard.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.dashboard.arn
          }
        }
      }
    ]
  })
}

# S3 bucket for raw data storage
resource "aws_s3_bucket" "data" {
  bucket = "${var.project_name}-data-${var.environment}"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "data" {
  bucket = aws_s3_bucket.data.id

  depends_on = [aws_s3_bucket_public_access_block.data]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontAccess"
        Effect    = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.data.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.data.arn
          }
        }
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
    domain_name              = aws_s3_bucket.dashboard.bucket_regional_domain_name
    origin_id                = "S3-${aws_s3_bucket.dashboard.id}"
    origin_access_control_id = aws_cloudfront_origin_access_control.dashboard.id
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

# CloudFront distribution for data bucket
resource "aws_cloudfront_distribution" "data" {
  enabled = true

  origin {
    domain_name              = aws_s3_bucket.data.bucket_regional_domain_name
    origin_id                = "S3-${aws_s3_bucket.data.id}"
    origin_access_control_id = aws_cloudfront_origin_access_control.dashboard.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.data.id}"
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 300
    max_ttl     = 3600
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

# Separate IAM roles for different Lambda functions
resource "aws_iam_role" "lambda_ingestor" {
  name = "${var.project_name}-lambda-ingestor-${var.environment}"

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

resource "aws_iam_role" "lambda_aggregator" {
  name = "${var.project_name}-lambda-aggregator-${var.environment}"

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

resource "aws_iam_role" "lambda_email" {
  name = "${var.project_name}-lambda-email-${var.environment}"

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

# Ingestor policy
resource "aws_iam_role_policy" "lambda_ingestor" {
  name = "${var.project_name}-lambda-ingestor-policy"
  role = aws_iam_role.lambda_ingestor.id

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
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${var.project_name}-ingestor-*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem"
        ]
        Resource = aws_dynamodb_table.raw_data.arn
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter/logistix/fred-api-key"
      }
    ]
  })
}

# Aggregator policy
resource "aws_iam_role_policy" "lambda_aggregator" {
  name = "${var.project_name}-lambda-aggregator-policy"
  role = aws_iam_role.lambda_aggregator.id

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
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${var.project_name}-aggregator-*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem"
        ]
        Resource = [
          aws_dynamodb_table.raw_data.arn,
          aws_dynamodb_table.daily_briefs.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.data.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter/logistix/openai-api-key"
      }
    ]
  })
}

# Email sender policy
resource "aws_iam_role_policy" "lambda_email" {
  name = "${var.project_name}-lambda-email-policy"
  role = aws_iam_role.lambda_email.id

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
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${var.project_name}-email-*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.daily_briefs.arn,
          aws_dynamodb_table.subscribers.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail"
        ]
        Resource = "arn:aws:ses:${var.aws_region}:*:identity/${var.sender_email}"
      }
    ]
  })
}

# Parameter Store for API keys
resource "aws_ssm_parameter" "openai_api_key" {
  name  = "/logistix/openai-api-key"
  type  = "SecureString"
  value = var.openai_api_key

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ssm_parameter" "fred_api_key" {
  name  = "/logistix/fred-api-key"
  type  = "SecureString"
  value = var.fred_api_key

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Lambda layer for news fetching
resource "aws_lambda_layer_version" "news_layer" {
  filename   = "layer.zip"
  layer_name = "${var.project_name}-news-layer-${var.environment}"
  compatible_runtimes = ["python3.11"]
}

# Lambda functions
resource "aws_lambda_function" "ingestor_fuel" {
  filename      = "ingestor-fuel.zip"
  function_name = "${var.project_name}-ingestor-fuel-${var.environment}"
  role          = aws_iam_role.lambda_ingestor.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 60
  layers        = [aws_lambda_layer_version.news_layer.arn]
  source_code_hash = filebase64sha256("ingestor-fuel.zip")

  environment {
    variables = {
      RAW_DATA_TABLE = aws_dynamodb_table.raw_data.name
      EIA_API_KEY    = var.eia_api_key
    }
  }
}

resource "aws_lambda_function" "ingestor_freight" {
  filename      = "ingestor-freight.zip"
  function_name = "${var.project_name}-ingestor-freight-${var.environment}"
  role          = aws_iam_role.lambda_ingestor.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 60
  layers        = [aws_lambda_layer_version.news_layer.arn]
  source_code_hash = filebase64sha256("ingestor-freight.zip")

  environment {
    variables = {
      RAW_DATA_TABLE = aws_dynamodb_table.raw_data.name
    }
  }
}

resource "aws_lambda_function" "ingestor_traffic" {
  filename      = "placeholder.zip"
  function_name = "${var.project_name}-ingestor-traffic-${var.environment}"
  role          = aws_iam_role.lambda_ingestor.arn
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
  role          = aws_iam_role.lambda_ingestor.arn
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
  filename      = "aggregator.zip"
  function_name = "${var.project_name}-aggregator-${var.environment}"
  role          = aws_iam_role.lambda_aggregator.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 300
  source_code_hash = filebase64sha256("aggregator.zip")

  environment {
    variables = {
      RAW_DATA_TABLE = aws_dynamodb_table.raw_data.name
      BRIEFS_TABLE   = aws_dynamodb_table.daily_briefs.name
      DATA_BUCKET    = aws_s3_bucket.data.id
    }
  }
}

resource "aws_lambda_function" "email_sender" {
  filename      = "placeholder.zip"
  function_name = "${var.project_name}-email-sender-${var.environment}"
  role          = aws_iam_role.lambda_email.arn
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

# New Lambda Functions

resource "aws_lambda_function" "ingestor_border_wait_times" {
  filename      = "placeholder.zip"
  function_name = "${var.project_name}-ingestor-border-wait-times-${var.environment}"
  role          = aws_iam_role.lambda_ingestor.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 60

  environment {
    variables = {
      RAW_DATA_TABLE = aws_dynamodb_table.raw_data.name
    }
  }
}

resource "aws_lambda_function" "ingestor_economic_data" {
  filename      = "placeholder.zip"
  function_name = "${var.project_name}-ingestor-economic-data-${var.environment}"
  role          = aws_iam_role.lambda_ingestor.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 60

  environment {
    variables = {
      RAW_DATA_TABLE          = aws_dynamodb_table.raw_data.name
      FRED_API_KEY_PARAM_NAME = aws_ssm_parameter.fred_api_key.name
    }
  }
}

resource "aws_lambda_function" "ingestor_air_traffic" {
  filename      = "placeholder.zip"
  function_name = "${var.project_name}-ingestor-air-traffic-${var.environment}"
  role          = aws_iam_role.lambda_ingestor.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 60

  environment {
    variables = {
      RAW_DATA_TABLE = aws_dynamodb_table.raw_data.name
    }
  }
}

resource "aws_lambda_function" "ingestor_ais_data" {
  filename      = "placeholder.zip"
  function_name = "${var.project_name}-ingestor-ais-data-${var.environment}"
  role          = aws_iam_role.lambda_ingestor.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 120 # Increased timeout for potential file download/processing

  environment {
    variables = {
      RAW_DATA_TABLE = aws_dynamodb_table.raw_data.name
    }
  }
}

resource "aws_lambda_function" "ingestor_global_events" {
  filename      = "placeholder.zip"
  function_name = "${var.project_name}-ingestor-global-events-${var.environment}"
  role          = aws_iam_role.lambda_ingestor.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 300 # Increased timeout for large file download/processing

  environment {
    variables = {
      RAW_DATA_TABLE = aws_dynamodb_table.raw_data.name
    }
  }
}

# New EventBridge targets for ingestion

resource "aws_cloudwatch_event_target" "border_wait_times" {
  rule      = aws_cloudwatch_event_rule.ingestion.name
  target_id = "border_wait_times"
  arn       = aws_lambda_function.ingestor_border_wait_times.arn
}

resource "aws_cloudwatch_event_target" "economic_data" {
  rule      = aws_cloudwatch_event_rule.ingestion.name
  target_id = "economic_data"
  arn       = aws_lambda_function.ingestor_economic_data.arn
}

resource "aws_cloudwatch_event_target" "air_traffic" {
  rule      = aws_cloudwatch_event_rule.ingestion.name
  target_id = "air_traffic"
  arn       = aws_lambda_function.ingestor_air_traffic.arn
}

resource "aws_cloudwatch_event_target" "ais_data" {
  rule      = aws_cloudwatch_event_rule.ingestion.name
  target_id = "ais_data"
  arn       = aws_lambda_function.ingestor_ais_data.arn
}

resource "aws_cloudwatch_event_target" "global_events" {
  rule      = aws_cloudwatch_event_rule.ingestion.name
  target_id = "global_events"
  arn       = aws_lambda_function.ingestor_global_events.arn
}

# New Lambda permissions for EventBridge

resource "aws_lambda_permission" "border_wait_times" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestor_border_wait_times.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ingestion.arn
}

resource "aws_lambda_permission" "economic_data" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestor_economic_data.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ingestion.arn
}

resource "aws_lambda_permission" "air_traffic" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestor_air_traffic.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ingestion.arn
}

resource "aws_lambda_permission" "ais_data" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestor_ais_data.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ingestion.arn
}

resource "aws_lambda_permission" "global_events" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestor_global_events.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ingestion.arn
}
