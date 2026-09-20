"""Ownership: add ``user_id`` to datasets and runs.

Adds the per-user owner key used by Supabase authentication. The column is
nullable and purely additive, so existing development/test rows are left
untouched — they are never deleted and never silently assigned to a user.

How existing (unowned) rows are treated is defined by application code in
``backend.app.db.repositories``:

- ``AUTH_MODE=disabled`` (dev/test): rows with ``user_id IS NULL`` belong to
  this environment's fixed ``local-dev`` identity, so pre-existing dev data
  stays visible and usable.
- ``AUTH_MODE=supabase``: rows with ``user_id IS NULL`` are visible only when
  they are shared system rows (bundled sample datasets flagged ``sample``);
  all other unowned rows are hidden from authenticated users.

The migration is dialect-agnostic (plain ``ALTER TABLE ... ADD COLUMN``) and
applies to both SQLite (dev/test) and Supabase PostgreSQL.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_user_ownership"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("datasets", sa.Column("user_id", sa.String(length=64), nullable=True))
    op.add_column("runs", sa.Column("user_id", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_datasets_user_id"), "datasets", ["user_id"], unique=False)
    op.create_index(op.f("ix_runs_user_id"), "runs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_runs_user_id"), table_name="runs")
    op.drop_index(op.f("ix_datasets_user_id"), table_name="datasets")
    op.drop_column("runs", "user_id")
    op.drop_column("datasets", "user_id")