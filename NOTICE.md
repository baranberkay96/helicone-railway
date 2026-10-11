# Notice

This is a community template. It is not affiliated with or endorsed by Helicone, Inc.

## Upstream software

| Component | License | Images used |
|---|---|---|
| Helicone (web, Jawn, migrations) | Apache-2.0, Copyright Helicone, Inc. | `helicone/web:v2025.08.21`, `helicone/jawn:v2025.08.21`, `helicone/migrations:v2025.08.21` |
| ClickHouse | Apache-2.0 | `clickhouse/clickhouse-server:24.3.18.7` |
| PostgreSQL | PostgreSQL License | `ghcr.io/railwayapp-templates/postgres-ssl:17` (Railway) |
| SeaweedFS | Apache-2.0 | `chrislusf/seaweedfs:4.48` |
| Caddy | Apache-2.0 | `caddy:2.11.7-alpine` |
| psycopg | LGPL-3.0 (installed unmodified from PyPI into the migrations image) | `psycopg[binary]==3.2.10` |

## Verified against

| What | Source | Version / ref | Checked |
|---|---|---|---|
| Services, buckets, variables | https://github.com/Helicone/helicone/blob/main/docker/docker-compose.yml, `docker/README.md`, `docker/.env.example` | main `067d9290` (2026-09-16) | 2026-10-11 |
| Release contents (all-in-one `Dockerfile`, `supervisord.conf`, `docker/dockerfiles/dockerfile_migrations`, `docker/dockerfiles/dockerfile_web`, `valhalla/dockerfile`) | GitHub tag `v2025.08.21-1` | 2025-08-21 | 2026-10-11 |
| Image publishing (tags only on releases) | `.github/workflows/docker-push.yml`, `docker/push_docker.sh`; Docker Hub tag lists | 2026-10-11 | 2026-10-11 |
| Production variables, `yarn serve`, migration runner, `/jawn` ingress path | https://github.com/Helicone/helicone-helm-v3 `charts/helicone-core` (values.yaml, `_helpers.tpl`, jawn/web deployments) | main `b70fe259` | 2026-10-11 |
| Public URL variables, on-prem flag, first-user SQL | https://docs.helicone.ai/getting-started/self-host/docker | docs | 2026-10-11 |
| Jawn routes, CORS, S3 client (path style, `S3_ENDPOINT_PUBLIC`), Redis client, ClickHouse/Postgres env | `valhalla/jawn/src/index.ts`, `controllers/public/proxyController.ts`, `lib/shared/db/s3Client.ts`, `lib/stores/request/request.ts`, `lib/clients/redisClient.ts`, `lib/db/ClickhouseWrapper.ts`, `lib/shared/db/dbExecute.ts` | tag `v2025.08.21-1` | 2026-10-11 |
| Better Auth config and user tables | `web/lib/auth.ts`, `supabase/migrations_without_supabase/20250416*.sql`, better-auth `v1.3.6` `src/crypto/password.ts` | tag `v2025.08.21-1` | 2026-10-11 |
| ClickHouse migrations and HQL user | `clickhouse/ch_hcone.py`, `clickhouse/migrations/schema_62*.sql`, `schema_64*.sql`, `clickhouse/seeds/*` | tag `v2025.08.21-1` | 2026-10-11 |
| Security fixes after the release | PR https://github.com/Helicone/helicone/pull/5816 | 2026-09-16 | 2026-10-11 |
| Railway Buckets (virtual-hosted style only) | https://docs.railway.com/storage-buckets | docs | 2026-10-11 |

## Adapted code

- `services/proxy/Caddyfile`: path layout follows the Jawn ingress of Helicone's Helm chart (`/jawn(/|$)(.*)`, Apache-2.0, Copyright Helicone, Inc.); written for Caddy.
- `services/migrations/railway-migrate.sh` calls the unmodified `/app/run-migrations.sh` from Helicone's migration image. `bootstrap.py` implements the first-user SQL from Helicone's Docker guide and Better Auth's password hash format (better-auth, MIT) in Python; no code copied.
- `services/seaweedfs/railway-seaweedfs.sh` is shared with this repository's PostHog template (written for these templates).
- `services/clickhouse` config written for this template from ClickHouse documentation.
- The Postgres service definition is copied from this repository's `_railway-base/postgres.json` (image tag 17 instead of 18, database name `helicone`).

## Reference only

- No Railway marketplace template or `_upstream` repository exists for Helicone; nothing else was used.

## Trademarks

Helicone is a trademark of Helicone, Inc. ClickHouse, PostgreSQL, SeaweedFS and Caddy belong to their respective owners.
