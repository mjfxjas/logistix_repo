# Dashboard Frontend

Minimal static dashboard for displaying daily logistics briefings.

## Files

- `index.html` - Main page structure
- `style.css` - Dark theme styling with responsive grid
- `app.js` - Fetches and renders briefing data from S3
- `sample-data.json` - Example data structure

## Local Testing

```bash
# Serve locally
python3 -m http.server 8080
# Visit http://localhost:8080
```

## Deployment

```bash
# Update API_BASE in app.js with your S3 bucket URL
# Then sync to S3
aws s3 sync . s3://logistix-dashboard-dev --exclude "*.md" --exclude "sample-data.json"
```

## Data Format

The dashboard expects JSON files at `{bucket}/{YYYY-MM-DD}.json` with:

```json
{
  "date": "2024-01-15",
  "ai_insight": "string",
  "fuel": {
    "national_avg": 3.45,
    "national_change": -1.2,
    "diesel": 4.12,
    "diesel_change": -3.2
  },
  "freight": {
    "dry_van": 2.15,
    "dry_van_change": 4.1,
    "reefer": 2.68,
    "reefer_change": 2.3,
    "flatbed": 2.92,
    "flatbed_change": 1.8
  },
  "traffic": [
    {"location": "string", "reason": "string"}
  ],
  "weather": [
    {"corridor": "string", "condition": "string"}
  ]
}
```
