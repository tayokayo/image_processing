"""Add component status management

Revision ID: b9051ad34412
Revises: 
Create Date: 2024-10-31 20:23:57.856805

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b9051ad34412'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('components', schema=None) as batch_op:
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('status', sa.Enum('PENDING', 'ACCEPTED', 'REJECTED', name='componentstatus'), nullable=True))
        batch_op.add_column(sa.Column('confidence_score', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('review_timestamp', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('reviewer_notes', sa.String(), nullable=True))

    with op.batch_alter_table('room_scenes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('total_components', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('pending_components', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('accepted_components', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('rejected_components', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('room_scenes', schema=None) as batch_op:
        batch_op.drop_column('rejected_components')
        batch_op.drop_column('accepted_components')
        batch_op.drop_column('pending_components')
        batch_op.drop_column('total_components')
        batch_op.drop_column('updated_at')

    with op.batch_alter_table('components', schema=None) as batch_op:
        batch_op.drop_column('reviewer_notes')
        batch_op.drop_column('review_timestamp')
        batch_op.drop_column('confidence_score')
        batch_op.drop_column('status')
        batch_op.drop_column('updated_at')

    # ### end Alembic commands ###
