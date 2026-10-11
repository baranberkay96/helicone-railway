# Helicone v2025.08 LLM Observability Gateway — Railway template spec

## Listing

- **Name:** Helicone v2025.08 LLM Observability Gateway (LISTINGS_ROUND2 base name with the pinned release label; Helicone versions its releases by date, `v2025.08.21`).
- **Description (70 chars):** Proxy, log and monitor every LLM request. Self-hosted with ClickHouse.
  - Changed from LISTINGS_ROUND2 ("Log, monitor and cache every LLM request. ..."): response caching lives in Helicone's Cloudflare worker / separate AI Gateway, not in the self-hosted Jawn proxy of this release, so the template cannot deliver it. Same length.
- **Category:** AI/ML
- **Tags:** helicone, llm, observability, ai-gateway, openai, anthropic, clickhouse, monitoring
- **Template repo:** `baranberkay96/helicone-railway` (this folder)

## Base

- **No market template exists** for Helicone (`_market/` is empty) and there is no `_upstream` repo.
- **Built from Helicone's own deployment sources:**
  - `Helicone/helicone` `docker/docker-compose.yml` (service list, MinIO buckets, Jawn/web variables) and `docker/README.md`,
  - the release tag `v2025.08.21-1` (all-in-one `Dockerfile`, `supervisord.conf`, `docker/dockerfiles/dockerfile_migrations`, `valhalla/dockerfile`),
  - Helicone's Helm chart `Helicone/helicone-helm-v3` `charts/helicone-core` (Apache-2.0): production variable set for web and Jawn, `yarn serve` for Jawn, migration runner, `/jawn` path routing,
  - the Docker self-hosting guide (https://docs.helicone.ai/getting-started/self-host/docker): public URL variables, `NEXT_PUBLIC_IS_ON_PREM`, first-user SQL.

## Pinned versions

Helicone publishes Docker images only for tagged releases. The latest release is `v2025.08.21-1` (2025-08-21); its images are tagged `v2025.08.21`, the same tag Helicone's Helm chart pins. `main` has moved on since (see Open questions), but no newer images exist.

| Service | Image | Tag | Notes |
|---|---|---|---|
| web | `helicone/web` | `v2025.08.21` | Next.js dashboard |
| jawn | `helicone/jawn` | `v2025.08.21` | API + LLM proxy |
| migrations (`services/migrations`) | `helicone/migrations` | `v2025.08.21` | + psycopg 3.2.10 and bootstrap script |
| clickhouse (`services/clickhouse`) | `clickhouse/clickhouse-server` | `24.3.18.7` | compose uses `24.3.13.40`; latest patch of the same line |
| Postgres | `ghcr.io/railwayapp-templates/postgres-ssl` | `17` | compose `postgres:17.4`, Helm `17.5` |
| seaweedfs (`services/seaweedfs`) | `chrislusf/seaweedfs` | `4.48` | replaces `minio/minio` |
| proxy (`services/proxy`) | `caddy` | `2.11.7-alpine` | |

Checked 2026-10-11.

## Architecture

```
 Browser / SDKs ── HTTPS ──> [proxy :8080 Caddy]
   /jawn/v1/gateway/{provider}/...  (LLM proxy) ──┐
   /jawn/*  (API used by the dashboard)          ├──> [jawn :8585] ──> LLM providers (OpenAI, Anthropic, ...)
   /request-response-storage/* (presigned) ──> [seaweedfs :8333]        │ logs: ClickHouse (metadata), S3 (bodies), Postgres (orgs, keys)
   everything else ──────────────────────────> [web :3000]              │
 web ──> Postgres (Better Auth, app data), ClickHouse, S3
 [migrations] (one-shot) ──> Postgres (Flyway), ClickHouse (schema), admin bootstrap
```

- Apps call the LLM through Jawn's proxy, e.g. OpenAI base URL `https://{domain}/jawn/v1/gateway/oai/v1` with the header `Helicone-Auth: Bearer {helicone-api-key}`. Jawn forwards the call, streams the answer back and logs it.
- The dashboard runs in the browser and calls Jawn at `https://{domain}/jawn` (same origin). Request/response bodies are fetched from SeaweedFS with presigned URLs under the same domain.
- No Redis, Kafka or MinIO: in this release Jawn's Redis client only connects over TLS without a password and the compose file wires no Redis into Jawn or web; Kafka is an "experimental" compose profile that is off by default; MinIO is replaced by SeaweedFS.

## Services

<!-- BEGIN SERVICES -->

### proxy

Caddy router on the only public domain: `/jawn/*` to Jawn (API and LLM proxy, prefix stripped, same layout as Helicone's Helm ingress), `/request-response-storage/*`, `/prompt-body-storage/*`, `/hql-store/*` to SeaweedFS (presigned downloads), everything else to the dashboard. Blocks Better Auth sign-up unless `HELICONE_ALLOW_SIGNUP=true` and hides Jawn's unauthenticated `/run-loops` debug route.

- Source: repo `baranberkay96/helicone-railway`, root directory `/services/proxy` (Dockerfile build)
- Start command: image default
- Pre-deploy command: none
- Healthcheck: `/_proxy/health` (timeout 120 s)
- Public domain: yes, target port `8080`
- TCP proxy: none
- Volume: none
- Restart policy: ALWAYS; replicas: 1; cron: none

| Variable | Value | Description |
|---|---|---|
| `PORT` | `8080` | Caddy listen port (public domain target). |
| `WEB_UPSTREAM` | `${{web.RAILWAY_PRIVATE_DOMAIN}}:3000` | Helicone dashboard (Next.js). |
| `JAWN_UPSTREAM` | `${{jawn.RAILWAY_PRIVATE_DOMAIN}}:8585` | Jawn API and LLM proxy. |
| `S3_UPSTREAM` | `${{seaweedfs.RAILWAY_PRIVATE_DOMAIN}}:8333` | SeaweedFS S3 (presigned body downloads). |
| `HELICONE_ALLOW_SIGNUP` | `false` | Set true to let new users sign up on /signup (they get their own organization). The admin account is created by the migrations service. |

### web

Helicone dashboard (Next.js, Better Auth login). Talks to Jawn through the public `/jawn` path from the browser and to Postgres/ClickHouse directly.

- Source: image `helicone/web:v2025.08.21`
- Start command: image default
- Pre-deploy command: none
- Healthcheck: `/api/hello` (timeout 1200 s)
- Public domain: no (private network only)
- TCP proxy: none
- Volume: none
- Restart policy: ALWAYS; replicas: 1; cron: none

| Variable | Value | Description |
|---|---|---|
| `PORT` | `3000` | Next.js port; Railway healthcheck probes it (/api/hello). |
| `NEXT_PUBLIC_APP_URL` | `https://${{proxy.RAILWAY_PUBLIC_DOMAIN}}` | Public URL of Helicone (the proxy domain). Change it when you add a custom domain to the proxy. |
| `SITE_URL` | `${{NEXT_PUBLIC_APP_URL}}` | Public dashboard URL. |
| `BETTER_AUTH_URL` | `${{NEXT_PUBLIC_APP_URL}}` | Better Auth base URL (must equal the public URL). |
| `BETTER_AUTH_TRUSTED_ORIGINS` | `${{NEXT_PUBLIC_APP_URL}}` | Origins allowed to call the auth endpoints. |
| `BETTER_AUTH_SECRET` | `${{secret(43, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")}}` | Signs session tokens. Generated once. |
| `NEXT_PUBLIC_BETTER_AUTH` | `true` | Use Better Auth (self-hosted auth) instead of Supabase auth. |
| `NEXT_PUBLIC_IS_ON_PREM` | `true` | Self-hosted mode (required off localhost). |
| `NEXT_PUBLIC_HELICONE_JAWN_SERVICE` | `${{NEXT_PUBLIC_APP_URL}}/jawn` | Jawn URL the browser uses (proxied under /jawn). |
| `NEXT_PUBLIC_API_BASE_PATH` | `${{NEXT_PUBLIC_APP_URL}}/jawn` | Helicone API base shown in the UI snippets. |
| `NEXT_PUBLIC_BASE_PATH` | `${{NEXT_PUBLIC_APP_URL}}/jawn/v1/gateway/oai/v1` | OpenAI-compatible proxy base URL shown in the onboarding snippets. |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Postgres (Better Auth and app data). |
| `SUPABASE_DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Postgres for Helicone's data access layer. |
| `DB_DRIVER` | `postgres` | Database driver (Helm value). |
| `DB_SSL` | `disable` | Plain connection on the private network. |
| `DB_HOST` | `${{Postgres.RAILWAY_PRIVATE_DOMAIN}}` | Postgres host. |
| `DB_PORT` | `5432` | Postgres port. |
| `DB_USER` | `${{Postgres.PGUSER}}` | Postgres user (reference). |
| `DB_PASSWORD` | `${{Postgres.PGPASSWORD}}` | Postgres password (reference). |
| `DB_NAME` | `${{Postgres.PGDATABASE}}` | Postgres database (reference). |
| `CLICKHOUSE_HOST` | `http://${{clickhouse.RAILWAY_PRIVATE_DOMAIN}}:8123` | ClickHouse HTTP endpoint. |
| `CLICKHOUSE_USER` | `default` | ClickHouse user. |
| `CLICKHOUSE_PASSWORD` | `${{clickhouse.CLICKHOUSE_PASSWORD}}` | ClickHouse password (reference). |
| `S3_ENDPOINT` | `http://${{seaweedfs.RAILWAY_PRIVATE_DOMAIN}}:8333` | SeaweedFS S3 endpoint (private network). |
| `S3_ACCESS_KEY` | `${{seaweedfs.AWS_ACCESS_KEY_ID}}` | S3 access key (reference). |
| `S3_SECRET_KEY` | `${{seaweedfs.AWS_SECRET_ACCESS_KEY}}` | S3 secret key (reference). |
| `S3_BUCKET_NAME` | `request-response-storage` | Bucket for request/response bodies. |
| `S3_FORCE_PATH_STYLE` | `true` | SeaweedFS needs path-style requests. |
| `VERCEL_ENV` | `development` | Must stay development for self-hosting (other values require Supabase TLS certificates). |
| `ENV` | `development` | Environment label (Helm value). |
| `ENABLE_PROMPT_SECURITY` | `false` | Prompt-injection model service is not deployed (Helm default). |
| `ENABLE_CRON_JOB` | `true` | Background loops (alerts, reports) - Helm default. |
| `SMTP_HOST` | `` | Optional SMTP server for verification and invite emails (outbound SMTP needs Railway Pro). |
| `SMTP_PORT` | `587` | SMTP port. |
| `SMTP_SECURE` | `false` | true for implicit TLS (port 465). |
| `SMTP_USER` | `` | SMTP username. |
| `SMTP_PASS` | `` | SMTP password. |
| `STRIPE_SECRET_KEY` | `sk_test_not_used_on_self_hosted` | Placeholder only: billing is not used on a self-hosted instance, but the Stripe client is created at start-up and needs a value (Helm/all-in-one images ship a dummy as well). |
| `OPENAI_API_KEY` | `sk-` | Placeholder Helicone's Helm chart sets; set a real key only if you want Helicone's own AI helpers. Your apps send their provider keys through the proxy. |
| `AZURE_API_KEY` | `anything` | Placeholder Helicone's Helm chart sets (Azure helper is unused). |
| `AZURE_API_VERSION` | `anything` | Placeholder Helicone's Helm chart sets. |
| `AZURE_DEPLOYMENT_NAME` | `anything` | Placeholder Helicone's Helm chart sets. |
| `AZURE_BASE_URL` | `anything` | Placeholder Helicone's Helm chart sets. |

### jawn

Helicone's API server and LLM proxy (`/v1/gateway/{provider}/...`): forwards requests to the LLM provider, logs request metadata to ClickHouse and bodies to S3, runs alerts and background loops. Started with `yarn serve` as in Helicone's Helm chart (the image default also starts a PyTorch prompt-security model).

- Source: image `helicone/jawn:v2025.08.21`
- Start command: `yarn serve`
- Pre-deploy command: none
- Healthcheck: `/healthcheck` (timeout 1200 s)
- Public domain: no (private network only)
- TCP proxy: none
- Volume: none
- Restart policy: ALWAYS; replicas: 1; cron: none

| Variable | Value | Description |
|---|---|---|
| `PORT` | `8585` | Jawn HTTP port; /healthcheck is the healthcheck. |
| `NEXT_PUBLIC_APP_URL` | `${{web.NEXT_PUBLIC_APP_URL}}` | Dashboard URL (CORS and links). |
| `SUPABASE_DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Postgres connection string. |
| `DB_HOST` | `${{Postgres.RAILWAY_PRIVATE_DOMAIN}}` | Postgres host. |
| `DB_PORT` | `5432` | Postgres port. |
| `DB_USER` | `${{Postgres.PGUSER}}` | Postgres user (reference). |
| `DB_PASSWORD` | `${{Postgres.PGPASSWORD}}` | Postgres password (reference). |
| `DB_NAME` | `${{Postgres.PGDATABASE}}` | Postgres database (reference). |
| `CLICKHOUSE_HOST` | `http://${{clickhouse.RAILWAY_PRIVATE_DOMAIN}}:8123` | ClickHouse HTTP endpoint. |
| `CLICKHOUSE_USER` | `default` | ClickHouse user. |
| `CLICKHOUSE_PASSWORD` | `${{clickhouse.CLICKHOUSE_PASSWORD}}` | ClickHouse password (reference). |
| `CLICKHOUSE_HQL_USER` | `hql_user` | Restricted ClickHouse user for HQL (SQL) queries from the UI. |
| `CLICKHOUSE_HQL_PASSWORD` | `${{migrations.CLICKHOUSE_HQL_PASSWORD}}` | Password the migrations service assigns to hql_user (reference). |
| `S3_ENDPOINT` | `http://${{seaweedfs.RAILWAY_PRIVATE_DOMAIN}}:8333` | SeaweedFS S3 endpoint for writes (private network). |
| `S3_ENDPOINT_PUBLIC` | `${{web.NEXT_PUBLIC_APP_URL}}` | Base for presigned URLs given to browsers; the proxy forwards bucket paths to SeaweedFS. |
| `S3_ACCESS_KEY` | `${{seaweedfs.AWS_ACCESS_KEY_ID}}` | S3 access key (reference). |
| `S3_SECRET_KEY` | `${{seaweedfs.AWS_SECRET_ACCESS_KEY}}` | S3 secret key (reference). |
| `S3_BUCKET_NAME` | `request-response-storage` | Bucket for request/response bodies. |
| `S3_PROMPT_BUCKET_NAME` | `prompt-body-storage` | Bucket for prompt bodies. |
| `HQL_STORE_BUCKET` | `hql-store` | Bucket for HQL result exports. |
| `BETTER_AUTH_SECRET` | `${{web.BETTER_AUTH_SECRET}}` | Must match web (validates sessions). |
| `BETTER_AUTH_URL` | `${{web.NEXT_PUBLIC_APP_URL}}` | Better Auth base URL. |
| `BETTER_AUTH_TRUSTED_ORIGINS` | `${{web.NEXT_PUBLIC_APP_URL}}` | Trusted origin for auth calls. |
| `NEXT_PUBLIC_BETTER_AUTH` | `true` | Better Auth mode. |
| `IS_HELICONE_CLOUD` | `false` | Self-hosted mode (CORS for the dashboard, no cloud features). |
| `HELICONE_WORKER_URL` | `http://localhost:8585/v1/gateway/oai` | Jawn's own OpenAI proxy route, used by the playground and experiments (all-in-one image value). |
| `VERCEL_ENV` | `development` | Must stay development for self-hosting (other values require Supabase TLS certificates). |
| `ENV` | `development` | Environment label (Helm value). |
| `ENABLE_PROMPT_SECURITY` | `false` | Prompt-security model is not started (Helm default). |
| `ENABLE_CRON_JOB` | `true` | Run Jawn's background loops (alerts, cleanups). |
| `STRIPE_SECRET_KEY` | `sk_test_not_used_on_self_hosted` | Placeholder only: billing is not used on a self-hosted instance, but the Stripe client is created at start-up and needs a value (Helm/all-in-one images ship a dummy as well). |
| `OPENAI_API_KEY` | `sk-` | Placeholder Helicone's Helm chart sets; set a real key only if you want Helicone's own AI helpers. Your apps send their provider keys through the proxy. |
| `AZURE_API_KEY` | `anything` | Placeholder Helicone's Helm chart sets (Azure helper is unused). |
| `AZURE_API_VERSION` | `anything` | Placeholder Helicone's Helm chart sets. |
| `AZURE_DEPLOYMENT_NAME` | `anything` | Placeholder Helicone's Helm chart sets. |
| `AZURE_BASE_URL` | `anything` | Placeholder Helicone's Helm chart sets. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `30` | Let in-flight proxied LLM calls finish on redeploy. |

### migrations

One-shot job on every deploy: waits for Postgres and ClickHouse, runs Helicone's migration image (Flyway + ClickHouse schema), sets the HQL user's password and creates the first admin account (verified email, password login, organization). Exits when done.

- Source: repo `baranberkay96/helicone-railway`, root directory `/services/migrations` (Dockerfile build)
- Start command: image default
- Pre-deploy command: none
- Healthcheck: none (no HTTP endpoint suitable for a deploy check)
- Public domain: no (private network only)
- TCP proxy: none
- Volume: none
- Restart policy: ON_FAILURE (max 10 retries); replicas: 1; cron: none

| Variable | Value | Description |
|---|---|---|
| `FLYWAY_URL` | `jdbc:postgresql://${{Postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/${{Postgres.PGDATABASE}}?sslmode=disable&options=-c%20search_path%3Dpublic,extensions` | JDBC URL for Flyway (Helm chart format). |
| `FLYWAY_USER` | `${{Postgres.PGUSER}}` | Postgres user (reference). |
| `FLYWAY_PASSWORD` | `${{Postgres.PGPASSWORD}}` | Postgres password (reference). |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Postgres connection string for the admin bootstrap. |
| `CLICKHOUSE_HOST` | `http://${{clickhouse.RAILWAY_PRIVATE_DOMAIN}}:8123` | ClickHouse HTTP endpoint. |
| `CLICKHOUSE_USER` | `default` | ClickHouse user. |
| `CLICKHOUSE_PASSWORD` | `${{clickhouse.CLICKHOUSE_PASSWORD}}` | ClickHouse password (reference). |
| `CLICKHOUSE_HQL_PASSWORD` | `${{secret(32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")}}` | Password set on the restricted hql_user (Helicone's migrations create it without one). |
| `HELICONE_ADMIN_EMAIL` | `` | Email of the first admin account (created once, email pre-verified). **(required input)** |
| `HELICONE_ADMIN_PASSWORD` | `${{secret(24, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")}}` | Password of the first admin account. Generated; read it here and change it after first login. |
| `HELICONE_ADMIN_NAME` | `Admin` | Display name of the first admin. |
| `HELICONE_ORG_NAME` | `My Organization` | Name of the admin's organization. |

### clickhouse

ClickHouse 24.3 (Helicone's compose line, latest patch) for request logs, scores and properties, with a generated password and a low-memory config.

- Source: repo `baranberkay96/helicone-railway`, root directory `/services/clickhouse` (Dockerfile build)
- Start command: image default
- Pre-deploy command: none
- Healthcheck: `/ping` (timeout 300 s)
- Public domain: no (private network only)
- TCP proxy: none
- Volume: `/var/lib/clickhouse`
- Restart policy: ON_FAILURE (max 10 retries); replicas: 1; cron: none

| Variable | Value | Description |
|---|---|---|
| `PORT` | `8123` | HTTP port; /ping is the healthcheck. |
| `CLICKHOUSE_PASSWORD` | `${{secret(32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")}}` | Password of the default (admin) user. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `60` | Let ClickHouse flush and stop cleanly. |

### Postgres

Railway base Postgres on the 17 line (Helicone's compose and Helm chart use Postgres 17), default database `helicone`.

- Source: image `ghcr.io/railwayapp-templates/postgres-ssl:17`
- Start command: image default
- Pre-deploy command: none
- Healthcheck: none (no HTTP endpoint suitable for a deploy check)
- Public domain: no (private network only)
- TCP proxy: none
- Volume: `/var/lib/postgresql/data`
- Restart policy: ON_FAILURE (max 10 retries); replicas: 1; cron: none

| Variable | Value | Description |
|---|---|---|
| `PGDATA` | `/var/lib/postgresql/data/pgdata` | Location where the database will be initialized |
| `PGHOST` | `${{RAILWAY_PRIVATE_DOMAIN}}` | Railway Private Domain Name. |
| `PGPORT` | `5432` | Port to connect to Postgres. |
| `PGUSER` | `${{ POSTGRES_USER }}` | Required variable for Data panel |
| `PGDATABASE` | `${{POSTGRES_DB}}` | Required variable for the data panel. |
| `PGPASSWORD` | `${{POSTGRES_PASSWORD}}` | Required variable for Data panel |
| `POSTGRES_DB` | `helicone` | Default database created when image is started. |
| `DATABASE_URL` | `postgresql://${{PGUSER}}:${{POSTGRES_PASSWORD}}@${{RAILWAY_PRIVATE_DOMAIN}}:5432/${{PGDATABASE}}` | URL to connect to Postgres database. |
| `POSTGRES_USER` | `postgres` | User to connect to Postgres DB |
| `SSL_CERT_DAYS` | `820` | SSL certificate expiry in days. |
| `POSTGRES_PASSWORD` | `${{ secret(32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") }}` | Password to connect to DB |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `60` | Allow Postgres to cleanly shut down |

### seaweedfs

SeaweedFS S3 store with generated credentials for request/response bodies, prompt bodies and HQL exports (buckets created at start). Replaces the MinIO container of Helicone's compose.

- Source: repo `baranberkay96/helicone-railway`, root directory `/services/seaweedfs` (Dockerfile build)
- Start command: image default
- Pre-deploy command: none
- Healthcheck: `/healthz` (timeout 300 s)
- Public domain: no (private network only)
- TCP proxy: none
- Volume: `/data`
- Restart policy: ON_FAILURE (max 10 retries); replicas: 1; cron: none

| Variable | Value | Description |
|---|---|---|
| `PORT` | `8333` | S3 port; /healthz is the healthcheck. |
| `S3_PORT` | `8333` | S3 gateway port. |
| `S3_BUCKETS` | `request-response-storage,prompt-body-storage,hql-store` | Buckets created at start (idempotent). |
| `AWS_ACCESS_KEY_ID` | `${{secret(20, "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")}}` | S3 access key (admin identity). |
| `AWS_SECRET_ACCESS_KEY` | `${{secret(40, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")}}` | S3 secret key. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `30` | Clean shutdown on redeploy. |

<!-- END SERVICES -->

## Upstream components not deployed, and why

| Upstream | Decision | Impact |
|---|---|---|
| `minio`, `minio-setup` | Replaced by SeaweedFS with generated credentials; buckets created by its entrypoint. | None. MinIO community images are discontinued. |
| `mailhog` | Dropped (development mail catcher). | Optional SMTP variables on web. The admin account is pre-verified, so no email is needed to start. |
| `redis` | Not deployed: nothing in this release's compose uses it, and Jawn's optional Redis client forces TLS and has no password setting. | Jawn uses its in-memory cache; rate limiting via Redis stays off (as in the compose stack). |
| `zookeeper`, `kafka` (profile `kafka`, "experimental") | Not deployed. | Jawn logs synchronously, the default for self-hosting. |
| `worker-*` (Cloudflare worker images, profile `workers`) | Not deployed; the worker images stopped at `v2025.06.04` and Jawn serves the proxy routes itself in this release. | None. |
| `jawn-dev`, `web-dev` | Development profile. | None. |
| Prompt-security Python service inside the Jawn image | Not started (`yarn serve`, `ENABLE_PROMPT_SECURITY=false`), as in the Helm chart. | No prompt-injection detection; saves ~1–2 GB RAM (PyTorch). |

## Improvements over upstream defaults

(No market template exists; these are improvements over Helicone's compose/all-in-one defaults.)

1. **First admin created automatically.** Helicone's Docker guide asks operators to sign up and then fix the account and organization with SQL in the database container. The `migrations` service creates a verified admin with a generated password (Better Auth-compatible hash, verified by signing in against the pinned web image) and names its organization.
2. **Sign-up closed by default** at the proxy (`HELICONE_ALLOW_SIGNUP=false`); the release's auth config has no switch for it. Jawn's unauthenticated `/run-loops` debug route is hidden.
3. **Generated secrets everywhere:** Better Auth secret (compose/all-in-one ship fixed defaults), ClickHouse password (compose: none), S3 keys (compose: `minioadmin`), Postgres password, and a password for the HQL user (Helicone creates it without one).
4. **One public domain** with path routing (`/jawn`, bucket paths, dashboard) like Helicone's Helm ingress, instead of exposing three ports (3000, 8585, 9080) publicly as the all-in-one guide does. No CORS or mixed-origin issues.
5. **No MinIO.** SeaweedFS S3 with credentials; presigned URLs signed for the public domain.
6. **Migrations wait for their databases** and are idempotent; web and Jawn restart until the schema exists (restart policy `ALWAYS`, 20-minute healthcheck windows).
7. **Jawn without the PyTorch side process**, as in the Helm chart (the image's default command also starts a prompt-security model).
8. **ClickHouse tuned for a container:** smaller caches, noisy system log tables off, 7-day TTL on query/part logs.

## Resource estimate

| Service | Idle RAM | Typical RAM | Typical vCPU | Volume |
|---|---|---|---|---|
| web | 0.35 GB | 0.6 GB | 0.1 | – |
| jawn | 0.4 GB | 0.8 GB | 0.2 | – |
| migrations (runs a few minutes per deploy, then exits) | 0 | 0 | 0 | – |
| clickhouse | 0.6 GB | 1.5 GB | 0.3 | 2–20 GB |
| Postgres | 0.1 GB | 0.3 GB | 0.05 | < 1 GB |
| seaweedfs | 0.08 GB | 0.2 GB | 0.03 | 1–50 GB (bodies) |
| proxy | 0.03 GB | 0.05 GB | 0.02 | – |
| **Total** | **~1.6 GB** | **~3.5 GB** | **~0.7** | **~4–70 GB** |

Railway prices: RAM $10/GB-month, vCPU $20/vCPU-month, volume $0.15/GB-month.

- **Idle:** 1.6 GB × $10 + ~0.1 vCPU × $20 + ~3 GB × $0.15 ≈ **$19/month**.
- **Typical (a team logging ~100k–1M LLM calls/month):** 3.5 GB × $10 + 0.7 vCPU × $20 + ~20 GB × $0.15 ≈ **$52/month**.
- Request/response bodies grow the SeaweedFS volume fastest.

**Minimum plan: Hobby.** Trial's 1 GB per service is tight for ClickHouse. Pro is recommended once stored bodies or ClickHouse data approach Hobby's 5 GB per-volume limit.

## Verification checklist

1. All services deploy; `migrations` logs end with `railway: migrations and bootstrap finished` and the service exits.
2. `https://{proxy-domain}/_proxy/health` returns `OK`; `https://{proxy-domain}/jawn/healthcheck` returns `{"status":"healthy :)"}`; `https://{proxy-domain}/api/hello` returns 200.
3. Sign in at `https://{proxy-domain}/signin` with `HELICONE_ADMIN_EMAIL` and `HELICONE_ADMIN_PASSWORD` (from the migrations service). The dashboard opens in your organization.
4. `POST https://{proxy-domain}/api/auth/sign-up/email` returns 403 (sign-up closed).
5. Create an API key in Settings > API Keys. Send a chat completion through `https://{proxy-domain}/jawn/v1/gateway/oai/v1` with `Authorization: Bearer {openai-key}` and `Helicone-Auth: Bearer {helicone-key}`; the request appears on the Requests page with tokens, cost and latency.
6. Open the request: the body loads (presigned URL via `/request-response-storage/...`).
7. Redeploy `clickhouse`, `Postgres`, `seaweedfs`; requests and bodies are still there. Redeploy `migrations`: logs show `No migrations to apply` and `admin ... already exists`.

## Open questions

- **Release age and fixes on `main`:** the newest images are from 2025-08-21. Helicone's `main` contains later fixes, including authorization fixes for organization owners reaching the platform admin API and an HQL tenant-isolation bypass (PR #5816, 2026-09-16). Exploiting them needs an organization account on the instance; keeping sign-up closed (default) limits the exposure to people you invite. No newer image exists; building `main` from source would also change the architecture (Jawn's LLM proxy routes were removed on `main` in favour of the separate AI Gateway).
- **Not deploy-tested on Railway.** Locally verified: migrations on Postgres 17 + ClickHouse 24.3 (186 Flyway migrations + all ClickHouse schema files, idempotent re-run), HQL user password, admin bootstrap and sign-in through the pinned web image, proxy routing and sign-up gate, SeaweedFS auth and presigned URLs.
- **Plan gating:** the database trigger creates organizations on the `enterprise` tier, so self-hosted features are not plan-limited; billing pages may still show Helicone Cloud plans.
- **Email:** without SMTP no verification, invite or password-reset emails are sent (outbound SMTP needs Railway Pro). Invited users can still be added by an admin; enabling sign-up temporarily (`HELICONE_ALLOW_SIGNUP=true`) lets teammates create accounts (unverified emails can sign in in this release).
- **Placeholders** (`STRIPE_SECRET_KEY`, `OPENAI_API_KEY=sk-`, `AZURE_*=anything`) mirror Helicone's Helm/all-in-one defaults so the Stripe/OpenAI clients initialise; they are not used for proxying.
