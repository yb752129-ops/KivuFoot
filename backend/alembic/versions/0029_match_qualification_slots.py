"""Link knockout winners to explicitly configured next-round slots.

Revision ID: 0029_match_qualification_slots
Revises: 0028_tirs_au_but
"""
from alembic import op
import sqlalchemy as sa

revision = "0029_match_qualification_slots"
down_revision = "0028_tirs_au_but"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "matchs_qualification_slots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_cible_id", sa.Integer(), nullable=False),
        sa.Column("cote", sa.String(length=10), nullable=False),
        sa.Column("match_source_id", sa.Integer(), nullable=False),
        sa.Column("cree_par_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("cote IN ('domicile','exterieur')", name="ck_qualification_slot_cote"),
        sa.ForeignKeyConstraint(["match_cible_id"], ["matchs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_source_id"], ["matchs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cree_par_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("match_cible_id", "cote", name="uq_qualification_slot_cible_cote"),
        sa.UniqueConstraint("match_source_id", name="uq_qualification_slot_source"),
    )
    op.create_index(
        "ix_matchs_qualification_slots_match_cible_id",
        "matchs_qualification_slots",
        ["match_cible_id"],
    )
    op.create_index(
        "ix_matchs_qualification_slots_match_source_id",
        "matchs_qualification_slots",
        ["match_source_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_matchs_qualification_slots_match_source_id", table_name="matchs_qualification_slots")
    op.drop_index("ix_matchs_qualification_slots_match_cible_id", table_name="matchs_qualification_slots")
    op.drop_table("matchs_qualification_slots")
