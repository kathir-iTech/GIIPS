"""feat: add watchlist, reassignment requests, complaint subscriptions, follow_up_count

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-30 20:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to existing tables
    op.add_column('complaints', sa.Column('follow_up_count', sa.Integer(), nullable=False, server_default='0'))

    # Create new tables
    op.create_table('watchlists',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('exec_user_id', sa.String(), nullable=False, index=True),
        sa.Column('incident_id', sa.String(), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_watchlists_id'), 'watchlists', ['id'], unique=False)

    op.create_table('incident_reassignment_requests',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('incident_id', sa.String(), nullable=False, index=True),
        sa.Column('requesting_officer_id', sa.String(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_incident_reassignment_requests_id'), 'incident_reassignment_requests', ['id'], unique=False)
    op.create_index(op.f('ix_incident_reassignment_requests_incident_id'), 'incident_reassignment_requests', ['incident_id'], unique=False)

    op.create_table('complaint_subscriptions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False, index=True),
        sa.Column('complaint_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_complaint_subscriptions_id'), 'complaint_subscriptions', ['id'], unique=False)
    op.create_index(op.f('ix_complaint_subscriptions_user_id'), 'complaint_subscriptions', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('complaint_subscriptions')
    op.drop_table('incident_reassignment_requests')
    op.drop_table('watchlists')
    op.drop_column('complaints', 'follow_up_count')
