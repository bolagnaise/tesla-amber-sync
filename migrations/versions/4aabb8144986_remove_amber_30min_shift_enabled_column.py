"""Remove amber_30min_shift_enabled column

Revision ID: 4aabb8144986
Revises: 15d97fe0510d
Create Date: 2025-11-10 22:12:51.245184

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4aabb8144986'
down_revision = '15d97fe0510d'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the amber_30min_shift_enabled column (no longer needed after nemTime fix)
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('amber_30min_shift_enabled')


def downgrade():
    # Restore the amber_30min_shift_enabled column if needed
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('amber_30min_shift_enabled', sa.Boolean(), nullable=True))
