"""feat: add peer_review, alert_config, response_template tables and columns

Revision ID: a1b2c3d4e5f6
Revises: 299d3a26a70c
Create Date: 2026-07-30 18:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '299d3a26a70c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to existing tables
    op.add_column('users', sa.Column('trust_score', sa.Float(), nullable=False, server_default='50.0'))
    op.add_column('incidents', sa.Column('estimated_cost', sa.Float(), nullable=True))
    op.add_column('complaints', sa.Column('predicted_resolution_days', sa.Float(), nullable=True))

    # Create new tables
    op.create_table('peer_reviews',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('incident_id', sa.String(), nullable=False, index=True),
        sa.Column('reviewer_id', sa.String(), nullable=False),
        sa.Column('reviewee_id', sa.String(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_peer_reviews_id'), 'peer_reviews', ['id'], unique=False)
    op.create_index(op.f('ix_peer_reviews_incident_id'), 'peer_reviews', ['incident_id'], unique=False)

    op.create_table('alert_configs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('exec_user_id', sa.String(), nullable=False, index=True),
        sa.Column('alert_type', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('threshold', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_configs_id'), 'alert_configs', ['id'], unique=False)
    op.create_index(op.f('ix_alert_configs_exec_user_id'), 'alert_configs', ['exec_user_id'], unique=False)

    op.create_table('response_templates',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('officer_id', sa.String(), nullable=False, index=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_response_templates_id'), 'response_templates', ['id'], unique=False)
    op.create_index(op.f('ix_response_templates_officer_id'), 'response_templates', ['officer_id'], unique=False)


def downgrade() -> None:
    op.drop_table('response_templates')
    op.drop_table('alert_configs')
    op.drop_table('peer_reviews')
    op.drop_column('complaints', 'predicted_resolution_days')
    op.drop_column('incidents', 'estimated_cost')
    op.drop_column('users', 'trust_score')
