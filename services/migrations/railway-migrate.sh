#!/bin/bash
# Runs on every deploy of the `migrations` service, then exits (restart policy ON_FAILURE).
#   1. wait until Postgres and ClickHouse accept connections,
#   2. Helicone's own migration script (Flyway + ClickHouse schema files),
#   3. bootstrap.py: HQL user password, first admin user and organization (idempotent).
set -euo pipefail

fail() { echo "FATAL: $*" >&2; exit 1; }
for v in FLYWAY_URL FLYWAY_USER FLYWAY_PASSWORD CLICKHOUSE_HOST CLICKHOUSE_USER CLICKHOUSE_PASSWORD DATABASE_URL; do
  [ -n "${!v:-}" ] || fail "$v must be set (see the template variables)."
done

wait_for() {
  local name="$1" host="$2" port="$3" i=0
  until (exec 3<>"/dev/tcp/${host}/${port}") 2>/dev/null; do
    i=$((i + 1))
    [ "$i" -le 180 ] || fail "$name at ${host}:${port} not reachable after 15 minutes"
    echo "railway: waiting for $name (${host}:${port})"
    sleep 5
  done
}

pg_hostport="$(python3 -c 'import os,urllib.parse as u; p=u.urlparse(os.environ["DATABASE_URL"]); print(p.hostname, p.port or 5432)')"
ch_hostport="$(python3 -c 'import os,urllib.parse as u; p=u.urlparse(os.environ["CLICKHOUSE_HOST"]); print(p.hostname, p.port or 8123)')"
wait_for Postgres ${pg_hostport}
wait_for ClickHouse ${ch_hostport}
until python3 -c 'import os,urllib.request as r; r.urlopen(os.environ["CLICKHOUSE_HOST"].rstrip("/") + "/ping", timeout=5)' 2>/dev/null; do
  echo "railway: waiting for ClickHouse /ping"; sleep 5
done

cd /app
/app/run-migrations.sh
python3 /app/railway/bootstrap.py
echo "railway: migrations and bootstrap finished"
