#!/bin/bash
# Thin wrapper around the official ClickHouse entrypoint for Helicone on Railway.
set -euo pipefail

if [ -z "${CLICKHOUSE_PASSWORD:-}" ]; then
  echo "FATAL: CLICKHOUSE_PASSWORD must be set." >&2
  exit 1
fi

# Fresh Railway volumes contain lost+found; ClickHouse does not need it.
rm -rf /var/lib/clickhouse/lost+found 2>/dev/null || true

exec /entrypoint.sh "$@"
