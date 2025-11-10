"""Update NULL Amber settings to False

Revision ID: 15d97fe0510d
Revises: e23c3eecc9a3
Create Date: 2025-11-10 21:46:35.783048

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '15d97fe0510d'
down_revision = 'e23c3eecc9a3'
branch_labels = None
depends_on = None


def upgrade():
    # Update existing NULL values to False (new default after nemTime fix)
    # The 30-minute shift is no longer needed for correct alignment
    op.execute("UPDATE user SET amber_30min_shift_enabled = 0 WHERE amber_30min_shift_enabled IS NULL")
    op.execute("UPDATE user SET amber_forecast_type = 'predicted' WHERE amber_forecast_type IS NULL")


def downgrade():
    # Revert to NULL if needed
    op.execute("UPDATE user SET amber_30min_shift_enabled = NULL WHERE amber_30min_shift_enabled = 0")
    op.execute("UPDATE user SET amber_forecast_type = NULL WHERE amber_forecast_type = 'predicted'")
