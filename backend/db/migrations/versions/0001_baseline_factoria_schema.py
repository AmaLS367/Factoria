"""Baseline Factoria schema

Revision ID: 0001
Revises: None
Create Date: 2026-05-18 13:42:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. runs
    op.create_table(
        "runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "started_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("finished_at", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="running"),
        sa.Column("input_file", sa.Text(), nullable=True),
        sa.Column("output_file", sa.Text(), nullable=True),
        sa.Column("model_name", sa.Text(), nullable=True),
        sa.Column("web_search_provider", sa.Text(), nullable=True),
    )

    # 2. items
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("runs.id"), nullable=True),
        sa.Column("identifier_column", sa.Text(), nullable=False),
        sa.Column("identifier_value", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="completed"),
        sa.Column(
            "created_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("prompt_tokens", sa.Integer(), server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), server_default="0"),
        sa.Column("llm_requests", sa.Integer(), server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float(), server_default="0.0"),
    )
    op.create_index(
        "idx_items_identifier",
        "items",
        ["identifier_column", "identifier_value"],
        unique=True,
    )

    # 3. item_fields
    op.create_table(
        "item_fields",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("field_name", sa.Text(), nullable=False),
        sa.Column("field_value", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "created_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("original_value", sa.Text(), nullable=True),
        sa.Column("review_status", sa.Text(), server_default="needs_review"),
        sa.Column("reviewed_at", sa.Text(), nullable=True),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_item_fields_item_id_name",
        "item_fields",
        ["item_id", "field_name"],
        unique=True,
    )

    # 4. item_sources
    op.create_table(
        "item_sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=True),
        sa.Column(
            "retrieved_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("credibility_score", sa.Float(), nullable=True),
    )

    # 5. jobs
    op.create_table(
        "jobs",
        sa.Column("job_id", sa.Text(), primary_key=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="queued"),
        sa.Column(
            "created_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("started_at", sa.Text(), nullable=True),
        sa.Column("finished_at", sa.Text(), nullable=True),
        sa.Column("total_items", sa.Integer(), server_default="0"),
        sa.Column("processed_items", sa.Integer(), server_default="0"),
        sa.Column("skipped_items", sa.Integer(), server_default="0"),
        sa.Column("failed_items", sa.Integer(), server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("input_file", sa.Text(), nullable=True),
        sa.Column("output_file", sa.Text(), nullable=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("runs.id"), nullable=True),
        sa.Column("sheet_name", sa.Text(), nullable=True),
        sa.Column("column_name", sa.Text(), nullable=True),
        sa.Column("target_fields", sa.Text(), nullable=True),
        sa.Column("item_label", sa.Text(), nullable=True),
        sa.Column("total_prompt_tokens", sa.Integer(), server_default="0"),
        sa.Column("total_completion_tokens", sa.Integer(), server_default="0"),
        sa.Column("total_llm_requests", sa.Integer(), server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float(), server_default="0.0"),
    )

    # 6. cache_entries
    op.create_table(
        "cache_entries",
        sa.Column("cache_key", sa.Text(), primary_key=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=True),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("expires_at", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_cache_kind_expires_at",
        "cache_entries",
        ["kind", "expires_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_cache_kind_expires_at", table_name="cache_entries")
    op.drop_table("cache_entries")
    op.drop_table("jobs")
    op.drop_table("item_sources")
    op.drop_index("idx_item_fields_item_id_name", table_name="item_fields")
    op.drop_table("item_fields")
    op.drop_index("idx_items_identifier", table_name="items")
    op.drop_table("items")
    op.drop_table("runs")
