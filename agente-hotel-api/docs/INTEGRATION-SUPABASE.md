# Supabase Integration Guide (ASIST_AGENTICO_HOTELERO)

This guide explains how to link your Supabase project to the Agente Hotel API without leaking secrets and while preserving local dev.

## What you need

- Supabase Project URL (API REST): `https://<project>.supabase.co`
- anon/public API key (safe for frontend with RLS)
- service_role API key (server-only, DO NOT commit)
- Postgres connection password (set/reset in Supabase "Database")

## Environment variables

Add the following to your environment file (do NOT commit real values):

```
# Supabase core
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_KEY=<anon-or-service_role-key>

# Use Supabase Postgres as primary DB for the API
# For SQLAlchemy + asyncpg, start with sslmode=require; see SSL notes below.
POSTGRES_URL=postgresql+asyncpg://postgres:<password>@db.<project>.supabase.co:5432/postgres?sslmode=require

# Optional plain libpq DSN
PG_CONNECTION_STRING=postgresql://postgres:<password>@db.<project>.supabase.co:5432/postgres
```

We added commented placeholders to `.env.example` so you can copy/paste safely.

## SSL considerations (asyncpg)

Supabase requires SSL. The `sslmode=require` URL param works for most setups. If you see SSL errors with asyncpg:

- Prefer passing an SSL context via SQLAlchemy `connect_args` in your settings, for example:

```python
# app/core/settings.py (example snippet)
from ssl import create_default_context
SSL_CTX = create_default_context()
# settings.construct_db_engine(..., connect_args={"ssl": SSL_CTX})
```

If you want, I can wire this automatically in `settings.py` using an env flag like `DB_SSL=1`.

## How the app picks the DB

The API uses `POSTGRES_URL` (SQLAlchemy URL) when present. To switch to Supabase:

1. Copy `.env.example` to `.env` and set the Supabase values.
2. Ensure your Docker Compose or local run exports the `.env`.
3. Start the stack; the API will use Supabase instead of the local Postgres container.

Local tests continue using the in-memory SQLite setup (as designed) and are unaffected.

## Using Supabase APIs from the backend

- Use `SUPABASE_URL` + `SUPABASE_KEY` only from server-side code. Avoid exposing `service_role` in any frontend.
- If you plan to call Supabase REST or storage from the API service, we can add a small helper client that reads those envs.

## Security best practices

- Never commit real credentials. Use placeholders in `.env.example` only.
- Store real keys in deployment secrets (e.g., Docker/VM env, GitHub Actions secrets).
- For frontend usage, only use the `anon` key with RLS enabled.

## Rollback to local Postgres

Simply remove/override `POSTGRES_URL` back to the local DSN:

```
POSTGRES_URL=postgresql+asyncpg://agente_user:<local_password>@postgres:5432/agente_hotel
```

## Troubleshooting

- Connection refused or SSL error: add `?sslmode=require` (already in the sample) or provide an SSL context via `connect_args`.
- Auth errors using service_role: ensure the key is not truncated and passed via environment only, not committed.
- Latency: Supabase DB is remote; expect higher RTT than local Postgres.

---
Need me to wire the optional SSL connect_args in `settings.py` now? I can add a minimal, safe toggle (`DB_SSL=1`) that doesn't affect local dev.
