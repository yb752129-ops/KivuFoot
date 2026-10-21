"""Convert legacy coach accounts to the unified club role.

Revision ID: 0024_role_coach_to_club
Revises: 0023_joueur_date_optional

Only accounts with a club scope are converted. If any coach account has no
club_id, the migration stops before changing rows so an administrator can
review and attach it safely. Existing club accounts are untouched. The
conversion map makes a rollback possible without deleting accounts.
"""

from alembic import op
import sqlalchemy as sa

revision = "0024_role_coach_to_club"
down_revision = "0023_joueur_date_optional"
branch_labels = None
depends_on = None

_ROLE_WITH_COACH = "'collecteur','organisateur','club_manager','coach','club','admin','supporter'"
_ROLE_CLUB_ONLY = "'collecteur','organisateur','club_manager','club','admin','supporter'"


def upgrade() -> None:
    bind = op.get_bind()
    orphans = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM users "
            "WHERE role = 'coach' AND club_id IS NULL"
        )
    ).scalar_one()
    if orphans:
        raise RuntimeError(
            f"0024 stopped: {orphans} coach account(s) have no club_id. "
            "Attach or review them before converting the legacy role. "
            "No user row was changed."
        )

    op.create_table(
        "role_coach_conversions",
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("old_role", sa.String(32), nullable=False),
        sa.Column("new_role", sa.String(32), nullable=False),
        sa.Column("converted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO role_coach_conversions (user_id, old_role, new_role)
            SELECT id, 'coach', 'club'
            FROM users
            WHERE role = 'coach'
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO audit_log
                (table_name, record_id, action, user_id, old_data, new_data)
            SELECT
                'users',
                id,
                'UPDATE',
                NULL,
                jsonb_build_object('role', 'coach', 'club_id', club_id),
                jsonb_build_object(
                    'role', 'club',
                    'club_id', club_id,
                    'motif', 'Unification du portail club'
                )
            FROM users
            WHERE role = 'coach'
            """
        )
    )
    op.execute(sa.text("UPDATE users SET role = 'club' WHERE role = 'coach'"))

    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint("ck_users_role", "users", f"role IN ({_ROLE_CLUB_ONLY})")


def downgrade() -> None:
    bind = op.get_bind()
    conflicts = bind.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM role_coach_conversions c
            JOIN users u ON u.id = c.user_id
            WHERE u.role <> 'club'
            """
        )
    ).scalar_one()
    if conflicts:
        raise RuntimeError(
            f"0024 downgrade stopped: {conflicts} converted account(s) no longer "
            "have role='club'; review role changes before rollback."
        )

    op.execute(
        sa.text(
            """
            INSERT INTO audit_log
                (table_name, record_id, action, user_id, old_data, new_data)
            SELECT
                'users',
                u.id,
                'UPDATE',
                NULL,
                jsonb_build_object('role', u.role, 'club_id', u.club_id),
                jsonb_build_object(
                    'role', 'coach',
                    'club_id', u.club_id,
                    'motif', 'Rollback de la conversion du portail club'
                )
            FROM users u
            JOIN role_coach_conversions c ON c.user_id = u.id
            """
        )
    )

    op.drop_constraint("ck_users_role", "users", type_="check")
    op.execute(
        sa.text(
            """
            UPDATE users u
            SET role = 'coach'
            FROM role_coach_conversions c
            WHERE c.user_id = u.id
            """
        )
    )
    op.create_check_constraint("ck_users_role", "users", f"role IN ({_ROLE_WITH_COACH})")
    op.drop_table("role_coach_conversions")
