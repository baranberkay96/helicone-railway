# SeaweedFS S3 store for Helicone on Railway (request/response bodies, prompt bodies,
# HQL result exports). Helicone's Jawn S3 client forces path-style requests against
# custom endpoints, which Railway Buckets (virtual-hosted style) do not accept, so the
# template uses SeaweedFS (Helicone's compose uses MinIO, which is no longer maintained).
FROM chrislusf/seaweedfs:4.48

COPY railway-seaweedfs.sh /usr/local/bin/railway-seaweedfs.sh
RUN chmod 0755 /usr/local/bin/railway-seaweedfs.sh

EXPOSE 8333

ENTRYPOINT ["/usr/local/bin/railway-seaweedfs.sh"]
