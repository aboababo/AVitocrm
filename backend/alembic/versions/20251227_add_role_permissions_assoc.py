"""add role_permissions_assoc table

Revision ID: add_role_permissions_assoc
Revises: initial
Create Date: 2025-12-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_role_permissions_assoc'
down_revision = 'initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'role_permissions_assoc',
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('permission_id', sa.Integer(), sa.ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )
    op.create_index(op.f('ix_role_permissions_assoc_role_id'), 'role_permissions_assoc', ['role_id'], unique=False)
    op.create_index(op.f('ix_role_permissions_assoc_permission_id'), 'role_permissions_assoc', ['permission_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_role_permissions_assoc_permission_id'), table_name='role_permissions_assoc')
    op.drop_index(op.f('ix_role_permissions_assoc_role_id'), table_name='role_permissions_assoc')
    op.drop_table('role_permissions_assoc')
