# ClickHouse for Helicone on Railway.
# Same 24.3 line as Helicone's docker-compose (24.3.13.40), latest 24.3 patch release,
# plus a small config override for a container with a few GB of RAM.
FROM clickhouse/clickhouse-server:24.3.18.7

COPY config.d/zz-railway.xml /etc/clickhouse-server/config.d/zz-railway.xml
COPY railway-entrypoint.sh /usr/local/bin/railway-entrypoint.sh
RUN chmod 0644 /etc/clickhouse-server/config.d/zz-railway.xml \
 && chmod 0755 /usr/local/bin/railway-entrypoint.sh

# The image entrypoint turns CLICKHOUSE_USER / CLICKHOUSE_PASSWORD into a users.d file;
# CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1 lets that user create the restricted HQL user
# and row policies that Helicone's migrations define.
ENV CLICKHOUSE_USER=default \
    CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1

EXPOSE 8123 9000

ENTRYPOINT ["/usr/local/bin/railway-entrypoint.sh"]
