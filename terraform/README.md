# Terraform Infrastructure

## Setup

1. **Configure variables**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

2. **Verify SES email**
   ```bash
   aws ses verify-email-identity --email-address your@email.com
   # Check email and click verification link
   ```

3. **Initialize and deploy**
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

## Resources Created

- **S3**: Dashboard bucket (public) + data bucket (private)
- **CloudFront**: CDN for dashboard
- **DynamoDB**: 3 tables (raw_data, daily_briefs, subscribers)
- **Lambda**: 6 functions (4 ingestors + aggregator + email sender)
- **EventBridge**: 2 schedules (5am ingestion, 6am email)
- **IAM**: Lambda execution role with necessary permissions

## Next Steps

After infrastructure is deployed:
1. Build Lambda function code
2. Update Lambda functions with actual code
3. Deploy dashboard to S3
4. Add test subscribers to DynamoDB
