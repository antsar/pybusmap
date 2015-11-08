"""empty message

Revision ID: 2ffc362958a
Revises: 2ac138deda5
Create Date: 2015-11-07 23:25:58.367874

"""

# revision identifiers, used by Alembic.
revision = '2ffc362958a'
down_revision = '2ac138deda5'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('stop', sa.Column('lat', sa.Float(), nullable=True))
    op.add_column('stop', sa.Column('lon', sa.Float(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('stop', 'lon')
    op.drop_column('stop', 'lat')
    ### end Alembic commands ###
