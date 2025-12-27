"""Merge initial and role_permissions_assoc

Revision ID: merged
Revises: ed6f1cb29d5a, initial
Create Date: 2025-12-26 23:25:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merged'
down_revision = ('ed6f1cb29d5a', 'initial')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass