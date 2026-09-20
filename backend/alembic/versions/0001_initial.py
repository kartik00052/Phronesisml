"""Initial schema — creates the full backend table set.

The tables are defined in ``backend.app.db.models``; this migration mirrors
them by replaying ``Base.metadata.create_all`` so the migration history and
the ORM stay in lockstep for the initial revision.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from backend.app.db import models as _models  # noqa: F401  (register tables on metadata)
from backend.app.db.database import Base

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
