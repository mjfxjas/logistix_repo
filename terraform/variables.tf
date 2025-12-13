variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "logistix"
}

variable "environment" {
  description = "Environment (dev, prod)"
  type        = string
  default     = "dev"
}

variable "openai_api_key" {
  description = "OpenAI API key for AI insights"
  type        = string
  sensitive   = true
}

variable "sender_email" {
  description = "Verified SES sender email"
  type        = string
}

variable "eia_api_key" {
  description = "EIA API key for fuel prices"
  type        = string
  sensitive   = true
  default     = ""
}

variable "traffic_511_key" {
  description = "511 SF Bay API key for traffic data"
  type        = string
  sensitive   = true
  default     = ""
}
