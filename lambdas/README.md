# Lambda Functions

All Lambda functions for the logistics briefing pipeline.

## Structure

```
lambdas/
├── ingestor-fuel/       # Fetch fuel prices from EIA API
├── ingestor-freight/    # Fetch freight spot rates
├── ingestor-traffic/    # Fetch traffic alerts from DOT
├── ingestor-weather/    # Fetch weather forecasts
├── aggregator/          # Combine data + generate AI insight
└── email-sender/        # Send HTML emails via SES
```

## Deployment

```bash
# Deploy all functions
./deploy.sh [project-name] [environment]

# Example
./deploy.sh logistix dev
```

## Testing Locally

```python
# Test individual function
cd ingestor-fuel
python3 -c "from index import handler; print(handler({}, {}))"
```

## API Integration TODOs

Replace mock data with real APIs:

1. **Fuel** - EIA API (requires free API key)
   - https://www.eia.gov/opendata/

2. **Freight** - Options:
   - DAT Freight & Analytics API (paid)
   - Truckstop.com API (paid)
   - FreightWaves SONAR (paid)

3. **Traffic** - DOT 511 APIs (free)
   - https://www.fhwa.dot.gov/trafficinfo/

4. **Weather** - Open-Meteo (free, no key required)
   - https://open-meteo.com/en/docs

## Environment Variables

Set in Terraform or AWS Console:

- Core stores: `RAW_DATA_TABLE`, `BRIEFS_TABLE`, `SUBSCRIBERS_TABLE`, `DATA_BUCKET`
- AI: `OPENAI_API_KEY` (local fallback) or SSM SecureString `/logistix/openai-api-key`
- Ingestors:
  - Fuel: `EIA_API_KEY`
  - Freight: optional vendor keys if added
  - Traffic: `TRAFFIC_511_KEY`, `AZ_511_KEY`, `UTAH_511_KEY`, `NY_511_KEY`
  - Economic data: `FRED_API_KEY_PARAM_NAME` (SSM parameter name holding the FRED key)
- Email/web: `SENDER_EMAIL` (SES verified), `DASHBOARD_URL` (CloudFront)

## Data Flow

```
EventBridge (5am) → Ingestors → DynamoDB (raw)
                                     ↓
                                Aggregator → OpenAI
                                     ↓
                    DynamoDB (briefs) + S3 (JSON)
                                     ↓
EventBridge (6am) → Email Sender → SES → Subscribers
```
