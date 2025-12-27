"""Add role_permissions_assoc table

Revision ID: ed6f1cb29d5a
Revises: 
Create Date: 2025-12-26 22:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ed6f1cb29d5a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create role_permissions_assoc table
    op.create_table(
        'role_permissions_assoc',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission')
    )
    op.create_index('ix_role_permissions_assoc_id', 'role_permissions_assoc', ['id'], unique=False)
    op.create_index('ix_role_permissions_assoc_role_id', 'role_permissions_assoc', ['role_id'], unique=False)
    op.create_index('ix_role_permissions_assoc_permission_id', 'role_permissions_assoc', ['permission_id'], unique=False)


def downgrade():
    op.drop_index('ix_role_permissions_assoc_permission_id', table_name='role_permissions_assoc')
    op.drop_index('ix_role_permissions_assoc_role_id', table_name='role_permissions_assoc')
    op.drop_index('ix_role_permissions_assoc_id', table_name='role_permissions_assoc')
    op.drop_table('role_permissions_assoc')