"""Add the third-place match phase without modifying existing matches."""
from alembic import op
import sqlalchemy as sa

revision = "0031_match_troisieme_place"
down_revision = "0030_prolongation_periods"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_matchs_phase", "matchs", type_="check")
    op.create_check_constraint("ck_matchs_phase", "matchs", "phase IN ('poule','barrage','quart','demi','3e_place','finale')")


def downgrade():
    n = op.get_bind().execute(sa.text("SELECT COUNT(*) FROM matchs WHERE phase = '3e_place'")).scalar_one()
    if n:
        raise RuntimeError("Cannot remove third-place support while third-place matches exist; no data changed.")
    op.drop_constraint("ck_matchs_phase", "matchs", type_="check")
    op.create_check_constraint("ck_matchs_phase", "matchs", "phase IN ('poule','barrage','quart','demi','finale')")
