from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text()


def test_coach_conversion_is_scoped_reversible_and_safe():
    migration = read("alembic/versions/0024_role_coach_to_club.py")
    assert 'down_revision = "0023_joueur_date_optional"' in migration
    assert "role = 'coach' AND club_id IS NULL" in migration
    assert "No user row was changed" in migration
    assert "role_coach_conversions" in migration
    assert "UPDATE users SET role = 'club' WHERE role = 'coach'" in migration
    assert "UPDATE users u" in migration
    assert "DELETE FROM users" not in migration.upper()


def test_coach_is_not_an_active_club_portal_role():
    rbac = read("app/auth/rbac.py")
    frontend_roles = read("../frontend-web/src/roles.js")
    admin_accounts = read("../frontend-web/src/pages/admin/Comptes.jsx")
    app = read("../frontend-web/src/App.jsx")
    assert "RoleUtilisateur.COACH" not in rbac.split("CLUB_ROLES", 1)[1].split("CLUB_ROLE_VALUES", 1)[0]
    assert '"coach"' not in frontend_roles.split("CLUB_ROLES", 1)[1].split(");", 1)[0]
    assert 'coach: "Club (legacy)"' not in admin_accounts
    assert '["club", "club_manager"]' in app


def test_admin_can_only_create_unified_club_role_for_team_accounts():
    users_route = read("app/routes/utilisateurs.py")
    assert "RoleUtilisateur.COACH" not in users_route
    assert "Rôle non attribuable ici : club, club_manager, collecteur ou organisateur." in users_route
    assert "Un compte club doit être rattaché à un club." in users_route
