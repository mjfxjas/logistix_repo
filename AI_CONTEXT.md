# AI Context (Universal)

Purpose: Logistics Morning Briefing — Lambda ingestors collect transportation signals, an aggregator produces a daily brief with AI analysis, and an email sender plus static web dashboard deliver it to subscribers.

Guardrails
- Do not add new cloud resources from this repo; Terraform already defines Lambda, DynamoDB, SES, S3/CloudFront, and Parameter Store.
- Keep secrets out of code and commits. Use SSM SecureString parameters for API keys; environment variables are only for local testing.
- Lambda runtime is Python 3.11; keep dependencies slim for cold-start performance and stay within AWS free tiers where possible.
- Prefer structured JSON outputs; brief files are stored as `{date}.json` in the data bucket and as JSON strings in DynamoDB.
- Logging should be concise and non-sensitive; avoid dumping prompts or credentials.

Key data flows
- Ingestors write daily module data to `RAW_DATA_TABLE` (DynamoDB). The aggregator reads modules (`fuel`, `freight`, `traffic`, `weather`, `border-wait-times`, `economic-data`, `air-traffic`, `ais-data`, `global-events`) and writes a combined brief to `BRIEFS_TABLE` and S3.
- Email sender reads the brief for the current date and sends an HTML summary via SES to active subscribers.
- Frontend pulls `{date}.json` from the data bucket/CloudFront; `web/sample-data.json` is for local testing.

Testing and safety
- Prefer lightweight local invocations (e.g., `python3 -c "from index import handler; handler({}, {})"`) and avoid hitting paid APIs in tests.
- When adding new sources, respect rate limits and licensing; add mock fallbacks where feasible.
- Align any AI usage with cost controls (short prompts, low temperature, small models unless quality requires otherwise).
