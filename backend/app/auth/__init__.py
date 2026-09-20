"""Supabase authentication — JWT verification + FastAPI request context.

The backend never issues tokens, never stores passwords, and never trusts a
user ID supplied by the client. The authenticated identity always comes from
a Supabase access token verified server-side (see ``verifier.py``).
"""