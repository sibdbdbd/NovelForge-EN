"""card revisions: server-side content snapshots before overwrites

Revision ID: 0007_card_revisions
Revises: 0006_budget_dispatch
Create Date: 2026-09-08 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0007_card_revisions'
down_revision: Union[str, None] = '0006_budget_dispatch'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'cardrevision',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('card_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('card_type_name', sa.String(), nullable=False, server_default=''),
        sa.Column('title', sa.String(), nullable=False, server_default=''),
        sa.Column('content', sa.JSON(), nullable=True),
        sa.Column('content_hash', sa.String(), nullable=False, server_default=''),
        sa.Column('reason', sa.String(), nullable=False, server_default='user_save'),
        sa.Column('actor', sa.String(), nullable=False, server_default='user'),
        sa.Column('chapter_number', sa.Integer(), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('note', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_cardrevision_card_id', 'cardrevision', ['card_id'])
    op.create_index('ix_cardrevision_project_id', 'cardrevision', ['project_id'])
    op.create_index('ix_cardrevision_card_type_name', 'cardrevision', ['card_type_name'])
    op.create_index('ix_cardrevision_content_hash', 'cardrevision', ['content_hash'])
    op.create_index('ix_cardrevision_reason', 'cardrevision', ['reason'])
    op.create_index('ix_cardrevision_chapter_number', 'cardrevision', ['chapter_number'])
    op.create_index('ix_cardrevision_card_created', 'cardrevision', ['card_id', 'created_at'])


def downgrade() -> None:
    for name in ('ix_cardrevision_card_created', 'ix_cardrevision_chapter_number', 'ix_cardrevision_reason', 'ix_cardrevision_content_hash', 'ix_cardrevision_card_type_name', 'ix_cardrevision_project_id', 'ix_cardrevision_card_id'):
        op.drop_index(name, table_name='cardrevision')
    op.drop_table('cardrevision')
