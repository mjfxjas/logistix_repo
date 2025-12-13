output "dashboard_url" {
  description = "CloudFront dashboard URL"
  value       = "https://${aws_cloudfront_distribution.dashboard.domain_name}"
}

output "dashboard_bucket" {
  description = "S3 dashboard bucket name"
  value       = aws_s3_bucket.dashboard.id
}

output "data_bucket" {
  description = "S3 data bucket name"
  value       = aws_s3_bucket.data.id
}

output "raw_data_table" {
  description = "DynamoDB raw data table name"
  value       = aws_dynamodb_table.raw_data.name
}

output "briefs_table" {
  description = "DynamoDB briefs table name"
  value       = aws_dynamodb_table.daily_briefs.name
}

output "subscribers_table" {
  description = "DynamoDB subscribers table name"
  value       = aws_dynamodb_table.subscribers.name
}

output "lambda_functions" {
  description = "Lambda function names"
  value = {
    fuel      = aws_lambda_function.ingestor_fuel.function_name
    freight   = aws_lambda_function.ingestor_freight.function_name
    traffic   = aws_lambda_function.ingestor_traffic.function_name
    weather   = aws_lambda_function.ingestor_weather.function_name
    aggregator = aws_lambda_function.aggregator.function_name
    email     = aws_lambda_function.email_sender.function_name
  }
}
