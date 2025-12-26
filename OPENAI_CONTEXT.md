# OpenAI Usage Context

Where used
- `lambdas/aggregator/index.py` calls OpenAI Chat Completions to generate a 2–3 sentence daily insight for the brief.
- Model: `gpt-4o-mini` (JSON over HTTPS via `urllib.request`).

Credentials
- Preferred: AWS SSM Parameter Store SecureString at `/logistix/openai-api-key`.
- Local/testing fallback: set `OPENAI_API_KEY` environment variable on the aggregator Lambda or during local runs.
- Do not log the key or include it in source control. Keep prompts and responses free of sensitive data.

Operational notes
- Timeout is 30s; keep prompts concise to reduce latency and cost.
- If the call fails or no key is available, the aggregator falls back to a deterministic plain-text summary.
- Consider retry/backoff wrapping if reliability becomes an issue; currently a single call is made per brief.
