"""Scope item uniqueness to (run_id, identifier_column, identifier_value)

Previously the unique index was on (identifier_column, identifier_value), which
prevented the same identifier from appearing in different runs. This migration
adds run_id to the unique index so each run has its own independent set of
identifiers.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-04 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("idx_items_identifier", table_name="items")
    op.create_index(
        "idx_items_identifier",
        "items",
        ["run_id", "identifier_column", "identifier_value"],
        unique=True,
    )


def downgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        """
        SELECT identifier_column, identifier_value, COUNT(*)
        FROM items
        GROUP BY identifier_column, identifier_value
        HAVING COUNT(*) > 1
        """
    )
    duplicates = result.fetchall()
    if duplicates:
        msg = (
            f"Cannot downgrade: {len(duplicates)} identifier(s) exist in multiple runs. "
            "Remove duplicate data before downgrading, or keep the run-scoped index."
        )
        raise ValueError(msg)
    op.drop_index("idx_items_identifier", table_name="items")
    op.create_index(
        "idx_items_identifier",
        "items",
        ["identifier_column", "identifier_value"],
        unique=True,
    )
