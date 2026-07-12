"""chatbot purpose field

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chatbot",
        sa.Column("purpose", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("chatbot", "purpose")
