# Helicone database migrations + first-admin bootstrap for Railway.
#
# Base: Helicone's own migration image (Flyway for Postgres, ch_hcone.py for ClickHouse),
# same release tag as web and jawn. Added: a wait for both databases, a password for the
# restricted ClickHouse HQL user, and an idempotent bootstrap of the first admin account
# and organization (the Docker guide does this with manual SQL).
FROM helicone/migrations:v2025.08.21

RUN pip install --no-cache-dir "psycopg[binary]==3.2.10"

COPY railway-migrate.sh /app/railway/railway-migrate.sh
COPY bootstrap.py /app/railway/bootstrap.py
RUN chmod 0755 /app/railway/railway-migrate.sh

CMD ["/app/railway/railway-migrate.sh"]
