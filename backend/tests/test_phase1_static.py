"""Fast, database-free phase 1 guardrails.

The integration suite still requires the project's PostgreSQL test service;
these checks run in any checkout and prevent the compatibility/security patch
from silently losing its key invariants.
"""
from pathlib import Path


ROOT = Path(__file__).parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_club_role_is_explicit_and_legacy_manager_shares_the_helper():
    rbac = read("app/auth/rbac.py")
    frontend = read("../frontend-web/src/roles.js")
    assert "RoleUtilisateur.CLUB" in rbac
    assert "RoleUtilisateur.COACH" not in rbac.split("CLUB_ROLES", 1)[1].split("CLUB_ROLE_VALUES", 1)[0]
    assert "RoleUtilisateur.CLUB_MANAGER" in rbac
    assert "def isClubRole" in rbac
    assert "export function isClubRole" in frontend
    assert '"club"' in frontend and '"coach"' not in frontend.split("CLUB_ROLES", 1)[1].split(");", 1)[0] and '"club_manager"' in frontend


def test_role_migration_is_additive_and_has_safe_downgrade():
    migration = read("alembic/versions/0022_role_club.py")
    assert "'club'" in migration
    assert "SELECT COUNT(*) FROM users WHERE role = 'club'" in migration
    assert "Downgrade 0022 refused" in migration
    assert "UPDATE users" not in migration.upper()
    assert "DELETE FROM users" not in migration.upper()


def test_live_match_player_registration_can_leave_birth_date_to_complete():
    model = read("app/models/joueur.py")
    schema = read("app/schemas/joueur.py")
    route = read("app/routes/joueurs.py")
    migration = read("alembic/versions/0023_joueur_date_naissance_optional.py")
    frontend = read("../frontend-web/src/pages/club/Effectif.jsx")
    assert "date | None" in model
    assert "date_naissance: date | None = None" in schema
    assert "payload.date_naissance is None" in route
    assert "nullable=True" in migration
    assert "dateJ || null" in frontend
    assert "ajout express" in frontend


def test_legacy_participations_are_not_removed_and_are_locked_and_audited():
    matchs = read("app/routes/matchs.py")
    assert '@router.post("/{match_id}/participations"' in matchs
    assert '@router.put("/{match_id}/participations/{participation_id}"' in matchs
    assert '@router.delete("/{match_id}/participations/{participation_id}"' in matchs
    assert 'select(Match).where(Match.id == match_id).with_for_update()' in matchs
    assert '"match_compositions"' in matchs
    assert "verifier_joueur(" in matchs


def test_documents_and_sensitive_club_views_require_authentication():
    documents = read("app/routes/documents.py")
    clubs = read("app/routes/clubs.py")
    assert "current_user: User = Depends(require_roles(*DOCUMENT_READ_ROLES))" in documents
    assert "async def telecharger_document" in documents
    assert "current_user: User = Depends(" in clubs
    assert 'async def lister_staff' in clubs


def test_validation_and_composition_use_row_locks():
    validation = read("app/services/validation.py")
    matchs = read("app/routes/matchs.py")
    assert "select(Match).where(Match.id == match_id).with_for_update()" in validation
    assert ".where(MatchParticipation.equipe_concernee == equipe)\n            .with_for_update()" in matchs
    assert "current_user.id" in matchs[matchs.index('"match_compositions"') :]
