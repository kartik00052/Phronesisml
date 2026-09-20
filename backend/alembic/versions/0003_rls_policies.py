"""Enable Row-Level Security on tenant tables for hosted Supabase Postgres.

HOSTED (Supabase) ONLY
======================
Supabase proxies Postgres behind PostgREST ("anon"/"authenticated" roles) and
gives the app a *different* connection than end users. The FastAPI backend
connects as a privileged role that bypasses RLS (service identity), while
client-side data access is meant to go ONLY through the backend — not through
PostgREST. RLS here exists as a defense-in-depth layer so that even a leaked
anon/authenticated key cannot read another user's rows directly through the
PostgreSQL wire.

Dev/test (SQLite)
=================
SQLite has no RLS concept. This migration therefore guards every statement
with a dialect check and is a structural no-op there, so `alembic upgrade
head` keeps working in local/test environments.

IMPORTANT — do NOT add `FORCE ROW LEVEL SECURITY` here.
The backend's own connection must keep working on these tables. If that role
lacks BYPASSRLS/superuser, `FORCE RLS` could lock the backend out of its own
data. Only enable `FORCE` on specific tables after confirming the service role
carries BYPASSRLS. Leave it off by default.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003_rls_policies"
down_revision: str | None = "0002_user_ownership"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES = (
    "datasets",
    "runs",
    "run_events",
    "pipeline_stages",
    "artifacts",
    "model_results",
)

# Parent tables own user_id; children are scoped through their run's owner.
PARENT_TABLES = ("datasets", "runs")


def _is_postgres() -> bool:
    return op.get_context().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        # Structural no-op on SQLite — RLS is a Postgres feature.
        return

    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")

    # Owner-scoped CRUD. The owner matches the authenticated Supabase user id.
    op.execute(
        "CREATE POLICY datasets_owner_all ON datasets "
        "USING ((user_id = (auth.uid())::text)) "
        "WITH CHECK ((user_id = (auth.uid())::text));"
    )
    op.execute(
        "CREATE POLICY datasets_shared_select ON datasets FOR SELECT USING ((user_id IS NULL));"
    )
    op.execute(
        "CREATE POLICY runs_owner_all ON runs "
        "USING ((user_id = (auth.uid())::text)) "
        "WITH CHECK ((user_id = (auth.uid())::text));"
    )

    # Child tables: SELECT-only, scoped through their run's owner. Writes go
    # through the backend's own role (bypasses RLS), so no client write
    # policies are granted — that keeps the client-side attack surface small.
    child_policies = (
        ("run_events", "run_events_run_owner_select"),
        ("pipeline_stages", "pipeline_stages_run_owner_select"),
        ("artifacts", "artifacts_run_owner_select"),
        ("model_results", "model_results_run_owner_select"),
    )
    for table, policy in child_policies:
        op.execute(
            f"CREATE POLICY {policy} ON {table} FOR SELECT "
            "USING (EXISTS ("
            "SELECT 1 FROM runs "
            "WHERE runs.id = {table}.run_id "
            "AND runs.user_id = (auth.uid())::text));".format(table=table)
        )

    # Column-level privileges: restrict what anon may touch; grant read to
    # authenticated. RLS policies and GRANTs are independent layers — both
    # must agree for PostgREST to behave.
    for table in TENANT_TABLES:
        op.execute(f"REVOKE ALL ON {table} FROM anon;")
        op.execute(f"GRANT SELECT ON {table} TO authenticated;")


def downgrade() -> None:
    if not _is_postgres():
        return

    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS datasets_owner_all ON datasets;")
    op.execute("DROP POLICY IF EXISTS datasets_shared_select ON datasets;")
    op.execute("DROP POLICY IF EXISTS runs_owner_all ON runs;")

    child_policies = (
        "run_events_run_owner_select",
        "pipeline_stages_run_owner_select",
        "artifacts_run_owner_select",
        "model_results_run_owner_select",
    )
    child_tables = ("run_events", "pipeline_stages", "artifacts", "model_results")
    for table, policy in zip(child_tables, child_policies, strict=True):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table};")

    for table in TENANT_TABLES:
        # Restore a sane default so downgrade+upgrade cycles stay tidy; safer
        # to be permissive on downgrade than to leave tables locked out.
        op.execute(f"GRANT ALL ON {table} TO anon;")
