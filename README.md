# Logistics Morning Briefing

Daily logistics intelligence delivered to truck drivers and dispatchers for $1/month.

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
EventBridge (5am) → 4 Ingestors → DynamoDB (raw)
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
├── lambdas/            # 6 Lambda functions (ingestors, aggregator, email)
├── web/                # Static dashboard (HTML/CSS/JS)
├── .env.example        # Environment variables template
└── README.md           # This file
```

## Cost Estimate

For 1,000 subscribers:
- Lambda: ~$3/month
- DynamoDB: ~$1/month
- SES: ~$0.10/month
- OpenAI: ~$20/month
- S3/CloudFront: ~$2/month

**Total: ~$26/month operating cost**
**Revenue: $1,000/month**
**Margin: 97%**

## API Integration

Current implementation uses mock data. To integrate real APIs:

1. **Fuel Prices** - Get free EIA API key at https://www.eia.gov/opendata/
2. **Freight Rates** - Subscribe to DAT or Truckstop.com API
3. **Traffic** - Use free DOT 511 APIs
4. **Weather** - Use free Open-Meteo API (no key required)

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

## Next Steps

- [ ] Integrate real API data sources
- [ ] Add subscriber management UI
- [ ] Implement Stripe billing (separate repo)
- [ ] Add historical data viewer
- [ ] Enable user preferences/customization
- [ ] Add mobile push notifications

## License

MIT
