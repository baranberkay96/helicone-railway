# Deploy and Host Helicone with Railway

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/helicone-v202508-llm-observability-gatew?referralCode=20H68q)

Helicone is an open-source LLM observability platform. Point your OpenAI or Anthropic client at Helicone's proxy and every request is logged with cost, latency, tokens and the full prompt and response. This community template deploys Helicone's self-hosted stack on Railway with ClickHouse, Postgres and S3 storage, and creates your admin account automatically.

## About Hosting Helicone

Self-hosted Helicone consists of a Next.js dashboard, the Jawn API server (which also proxies LLM calls), Postgres for accounts, organizations and API keys, ClickHouse for request analytics, and S3-compatible storage for request and response bodies. Helicone's own Docker guide runs everything in one container and has you fix the first account with SQL. This template splits the services the way Helicone's Helm chart does, puts them behind one HTTPS domain with path routing, runs the database migrations as a job, creates a verified admin account and organization, closes public sign-up, and generates every secret, so you can log in and send your first request a few minutes after deploying.

## Common Use Cases

- Log every LLM call from your apps with cost, latency and token usage per user, feature or custom property.
- Debug agents and multi-step chains with sessions and the full request and response bodies.
- Track spend across OpenAI and Anthropic and set alerts on errors or cost.
- Keep prompts and completions inside your own infrastructure for privacy or compliance.
- Query your LLM traffic with HQL (SQL over your logs) and export datasets.

## Dependencies for Helicone Hosting

- Helicone images `helicone/web`, `helicone/jawn` and `helicone/migrations`, release `v2025.08.21`
- ClickHouse 24.3
- PostgreSQL 17 (Railway Postgres)
- SeaweedFS (S3-compatible storage)
- Caddy (router on the public domain)

### Deployment Dependencies

- Helicone self-hosting (Docker): https://docs.helicone.ai/getting-started/self-host/docker
- Helicone repository and compose file: https://github.com/Helicone/helicone/tree/main/docker
- Helicone Helm chart: https://github.com/Helicone/helicone-helm-v3
- Helicone headers reference: https://docs.helicone.ai/helicone-headers/header-directory
- SeaweedFS S3 API: https://github.com/seaweedfs/seaweedfs/wiki/Amazon-S3-API

### Implementation Details

| Service | Role | Public | Storage |
|---|---|---|---|
| proxy | Caddy router: `/jawn/*` to Jawn, bucket paths to SeaweedFS, rest to the dashboard; sign-up gate | Yes | – |
| web | Helicone dashboard (Next.js, Better Auth) | No | – |
| jawn | API server and LLM proxy (`/jawn/v1/gateway/oai/v1`, `/jawn/v1/gateway/anthropic`) | No (via proxy) | – |
| migrations | One-shot job: database migrations and first admin account | No | – |
| clickhouse | Request analytics | No | Volume |
| Postgres | Accounts, organizations, API keys, prompts | No | Volume |
| seaweedfs | Request and response bodies | No (presigned via proxy) | Volume |

**First login**

1. Enter your email in `HELICONE_ADMIN_EMAIL` when deploying (the only required input).
2. Wait until `migrations` has finished (its logs end with `migrations and bootstrap finished`).
3. Open `https://{your-proxy-domain}/signin` and sign in with that email and the generated `HELICONE_ADMIN_PASSWORD` from the `migrations` service variables.
4. Create a Helicone API key in Settings, then point your client at the proxy:
   - OpenAI: base URL `https://{your-proxy-domain}/jawn/v1/gateway/oai/v1`, header `Helicone-Auth: Bearer {your-helicone-key}`
   - Anthropic: base URL `https://{your-proxy-domain}/jawn/v1/gateway/anthropic`, same header

Your provider API key stays in your app and is passed through to the provider.

**Teammates:** public sign-up is closed. Set `HELICONE_ALLOW_SIGNUP=true` on `proxy` while teammates create accounts, then switch it back. Verification and invite emails need SMTP settings on `web` (outbound SMTP requires a Railway Pro plan).

**Scaling:** `jawn` and `web` are stateless and can run more replicas; Jawn carries the proxied LLM traffic. ClickHouse scales vertically.

**Pinning and upgrades:** web, jawn and migrations are pinned to Helicone's release tag `v2025.08.21` (the latest published images, also used by Helicone's Helm chart). Upgrade all three together to a newer release tag and redeploy; `migrations` applies new schema changes. ClickHouse is pinned in `services/clickhouse/Dockerfile`.

**Resources:** about 1.6 GB RAM idle (around $19/month); a team logging up to a million requests a month typically uses about 3.5 GB (around $50/month). Hobby plan works; Pro helps once stored bodies grow past 5 GB.

### Why Deploy Helicone on Railway?

Railway runs the dashboard, API, databases and storage as one project with private networking, volumes, generated secrets and usage-based billing. You get a self-hosted LLM observability stack on your own domain without managing servers, and your prompts and completions never leave your project.
