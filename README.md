# Logistics Morning Briefing

Scheduled logistics briefings built from Lambda ingestors, a summarization step, a static dashboard, and SES email delivery.

## Quick Start

### 1. Deploy Infrastructure

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

terraform init
terraform apply
```

### 2. Verify SES Email

```bash
aws ses verify-email-identity --email-address your@email.com
# Check email and click verification link
```

### 3. Deploy Lambda Functions

```bash
cd lambdas
./deploy.sh logistix dev
```

### 4. Deploy Dashboard

```bash
# Update API_BASE in web/app.js with your S3 bucket URL
cd web
aws s3 sync . s3://logistix-dashboard-dev
```

### 5. Add Test Subscriber

```bash
aws dynamodb put-item \
    --table-name logistix-subscribers-dev \
    --item '{"email": {"S": "test@example.com"}, "active": {"BOOL": true}}'
```

## Architecture

```
EventBridge (5am) → Ingestors (fuel, freight, traffic, weather, border waits, econ, air/sea) → DynamoDB (raw)
                                       ↓
                                  Aggregator → OpenAI
                                       ↓
                      DynamoDB (briefs) + S3 (JSON)
                                       ↓
EventBridge (6am) → Email Sender → SES → Subscribers
                                       ↓
                            S3 + CloudFront → Dashboard
```

## Project Structure

```
logistix_repo/
├── terraform/          # AWS infrastructure (S3, Lambda, DynamoDB, etc.)
├── lambdas/            # Ingestors, aggregator, and email sender
├── web/                # Static dashboard (HTML/CSS/JS)
├── .env.example        # Environment variables template
└── README.md           # This file
```

## API Integration

Some ingestors use mock data or mock fallbacks. Configure and verify each source before using its output:

1. **Fuel Prices** - Configure an EIA API key: https://www.eia.gov/opendata/
2. **Freight Rates** - Subscribe to DAT or Truckstop.com API
3. **Traffic** - Configure DOT 511 APIs
4. **Weather** - Configure the Open-Meteo integration

Update the respective Lambda functions in `lambdas/ingestor-*/index.py`

## Testing

### Test Lambda Locally
```bash
cd lambdas/ingestor-fuel
python3 -c "from index import handler; print(handler({}, {}))"
```

### Test Dashboard Locally
```bash
cd web
python3 -m http.server 8080
# Visit http://localhost:8080
```

### Trigger Manual Run
```bash
# Trigger ingestion
aws lambda invoke --function-name logistix-ingestor-fuel-dev /dev/stdout

# Trigger aggregation
aws lambda invoke --function-name logistix-aggregator-dev /dev/stdout

# Trigger email
aws lambda invoke --function-name logistix-email-sender-dev /dev/stdout
```

## Monitoring

```bash
# View Lambda logs
aws logs tail /aws/lambda/logistix-aggregator-dev --follow

# Check DynamoDB items
aws dynamodb scan --table-name logistix-briefs-dev

# List S3 files
aws s3 ls s3://logistix-data-dev/
```

## License

MIT
