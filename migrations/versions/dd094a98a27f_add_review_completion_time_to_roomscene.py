"""Add review_completion_time to RoomScene

Revision ID: dd094a98a27f
Revises: b9051ad34412
Create Date: 2024-11-01 13:43:56.870150

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dd094a98a27f'
down_revision = 'b9051ad34412'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('room_scenes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('review_completion_time', sa.DateTime(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('room_scenes', schema=None) as batch_op:
        batch_op.drop_column('review_completion_time')

    # ### end Alembic commands ###
