# Helicone router for Railway: stock Caddy with a path-based routing table.
FROM caddy:2.11.7-alpine

COPY Caddyfile /etc/caddy/Caddyfile

# Fail the build early if the config does not parse.
RUN caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

EXPOSE 8080

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
