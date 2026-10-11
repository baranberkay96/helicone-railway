"""Post-migration steps for Helicone on Railway (idempotent, safe to run on every deploy).

1. Give ClickHouse's restricted `hql_user` (created by Helicone's migrations without a
   password) the password from CLICKHOUSE_HQL_PASSWORD.
2. Create the first admin account when HELICONE_ADMIN_EMAIL is set and no user with that
   email exists: a Better Auth user (email marked verified) with an email/password
   credential. Helicone's own database trigger then creates the personal organization
   and owner membership; the script names it and marks onboarding done. Helicone's
   Docker guide has operators do the equivalent by hand with SQL.

Password hashing follows Better Auth 1.3 (the version in the pinned web image):
scrypt(N=16384, r=16, p=1, dkLen=64) over the NFKC password with the hex salt string as
salt, stored as "<salt-hex>:<key-hex>".
"""
import hashlib
import os
import secrets
import string
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

import psycopg

ID_ALPHABET = string.ascii_letters + string.digits


def log(msg: str) -> None:
    print(f"railway: {msg}", flush=True)


def clickhouse(query: str) -> None:
    host = os.environ["CLICKHOUSE_HOST"].rstrip("/")
    req = urllib.request.Request(
        f"{host}/?{urllib.parse.urlencode({'query': query})}",
        method="POST",
        headers={
            "X-ClickHouse-User": os.environ.get("CLICKHOUSE_USER", "default"),
            "X-ClickHouse-Key": os.environ["CLICKHOUSE_PASSWORD"],
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()


def set_hql_password() -> None:
    password = os.environ.get("CLICKHOUSE_HQL_PASSWORD", "")
    if not password:
        log("CLICKHOUSE_HQL_PASSWORD not set; leaving hql_user unchanged")
        return
    if any(c not in ID_ALPHABET for c in password):
        sys.exit("FATAL: CLICKHOUSE_HQL_PASSWORD must be alphanumeric")
    try:
        clickhouse(f"ALTER USER IF EXISTS hql_user IDENTIFIED WITH sha256_password BY '{password}'")
        log("hql_user password set")
    except urllib.error.HTTPError as exc:
        sys.exit(f"FATAL: could not set hql_user password: {exc.read().decode(errors='replace')[:500]}")


def better_auth_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.scrypt(
        unicodedata.normalize("NFKC", password).encode(),
        salt=salt.encode(),
        n=16384, r=16, p=1, dklen=64, maxmem=128 * 16384 * 16 * 2,
    )
    return f"{salt}:{key.hex()}"


def new_id(length: int = 32) -> str:
    return "".join(secrets.choice(ID_ALPHABET) for _ in range(length))


def bootstrap_admin() -> None:
    email = os.environ.get("HELICONE_ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("HELICONE_ADMIN_PASSWORD", "")
    if not email:
        log("HELICONE_ADMIN_EMAIL not set; skipping admin bootstrap")
        return
    if len(password) < 8:
        sys.exit("FATAL: HELICONE_ADMIN_PASSWORD must have at least 8 characters")
    org_name = os.environ.get("HELICONE_ORG_NAME", "My Organization")

    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM public."user" WHERE lower(email) = %s', (email,))
            if cur.fetchone():
                log(f"admin {email} already exists; nothing to do")
                return
            user_id = new_id()
            cur.execute(
                'INSERT INTO public."user" (id, name, email, "emailVerified", "createdAt", "updatedAt") '
                "VALUES (%s, %s, %s, true, now(), now()) RETURNING auth_user_id",
                (user_id, os.environ.get("HELICONE_ADMIN_NAME", "Admin"), email),
            )
            auth_user_id = cur.fetchone()[0]
            cur.execute(
                'INSERT INTO public.account (id, "accountId", "providerId", "userId", password, "createdAt", "updatedAt") '
                "VALUES (%s, %s, 'credential', %s, %s, now(), now())",
                (new_id(), user_id, user_id, better_auth_hash(password)),
            )
            # Helicone's database creates a personal organization (owner role) when a user
            # row is added. Reuse it; create one only if that trigger did not run.
            cur.execute(
                "SELECT organization FROM public.organization_member WHERE member = %s LIMIT 1",
                (auth_user_id,),
            )
            row = cur.fetchone()
            if row:
                org_id = row[0]
                cur.execute(
                    'UPDATE public.organization_member SET "user" = %s WHERE member = %s AND organization = %s',
                    (user_id, auth_user_id, org_id),
                )
            else:
                cur.execute(
                    "INSERT INTO public.organization (name, is_personal, owner) VALUES (%s, true, %s) RETURNING id",
                    (org_name, auth_user_id),
                )
                org_id = cur.fetchone()[0]
                cur.execute(
                    'INSERT INTO public.organization_member ("user", member, organization, org_role) '
                    "VALUES (%s, %s, %s, 'owner')",
                    (user_id, auth_user_id, org_id),
                )
            # Skip the cloud onboarding wizard (plan selection) for the bootstrap account.
            cur.execute(
                "UPDATE public.organization SET name = %s, has_onboarded = true WHERE id = %s",
                (org_name, org_id),
            )
        conn.commit()
    log(f"created admin {email} in organization '{org_name}'")


if __name__ == "__main__":
    set_hql_password()
    bootstrap_admin()
