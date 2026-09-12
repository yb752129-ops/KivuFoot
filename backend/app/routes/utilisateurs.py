"""Gestion ADMIN des comptes réels du championnat.

Principes (mission du 12 septembre 2026, aucune exception) :
- l'admin ne choisit, ne voit et ne reçoit JAMAIS un mot de passe ;
- la création d'un compte génère un code d'activation à usage unique,
  stocké uniquement haché (SHA-256) et montré UNE seule fois : la personne
  choisit ensuite son propre mot de passe via POST /auth/activation ;
- la réinitialisation fonctionne pareillement : nouveau code, sessions
  immédiatement révoquées, aucun mot de passe généré ni affiché ;
- aucune route ici ne renvoie mot_de_passe_hash ni jeton brut stocké.
"""
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.hashing import hash_password
from app.auth.rbac import require_roles
from app.database import get_db
from app.models.club import Club
from app.models.enums import ActionAudit, RoleUtilisateur
from app.models.user import RefreshToken, User
from app.routes.auth import _hash_jeton, _nouveau_jeton_activation, _revoquer_sessions
from app.schemas.auth import AdminUserCreate, AdminUserOut, AdminUserUpdate, CreationCompteOut
from app.services.audit import log_audit

router = APIRouter(prefix="/admin/utilisateurs", tags=["Comptes (admin)"])

# Seuls les rôles du championnat sont attribuables ici. `admin` ne se
# multiplie pas via cette route ; `supporter` passe par l'inscription publique.
ROLES_ATTRIBUABLES = {
    RoleUtilisateur.COACH,
    RoleUtilisateur.CLUB_MANAGER,
    RoleUtilisateur.COLLECTEUR,
    RoleUtilisateur.ORGANISATEUR,
}
ROLES_A_CLUB = {RoleUtilisateur.COACH, RoleUtilisateur.CLUB_MANAGER}

ROLE_LIBELLE = {
    RoleUtilisateur.COACH: "coach",
    RoleUtilisateur.CLUB_MANAGER: "club_manager",
    RoleUtilisateur.COLLECTEUR: "collecteur",
    RoleUtilisateur.ORGANISATEUR: "organisateur",
}


def _role_value(role) -> str:
    return role.value if hasattr(role, "value") else str(role)


def _out(user: User) -> AdminUserOut:
    return AdminUserOut.model_validate(user).model_copy(
        update={"activation_en_attente": bool(user.jeton_activation_hash)}
    )


async def _verifier_club(db: AsyncSession, club_id: int | None) -> None:
    if club_id is None:
        return
    club = await db.get(Club, club_id)
    if club is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Club introuvable.")


@router.get("", response_model=list[AdminUserOut])
async def lister_utilisateurs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN)),
):
    result = await db.execute(select(User).order_by(User.id))
    return [_out(u) for u in result.scalars().all()]


@router.post("", response_model=CreationCompteOut, status_code=status.HTTP_201_CREATED)
async def creer_utilisateur(
    payload: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN)),
):
    role = payload.role if isinstance(payload.role, RoleUtilisateur) else RoleUtilisateur(_role_value(payload.role))
    if role not in ROLES_ATTRIBUABLES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Rôle non attribuable ici : coach, club, collecteur ou organisateur.",
        )
    email = str(payload.email).lower()
    existant = await db.execute(select(User).where(User.email == email))
    if existant.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Un compte existe déjà avec cet e-mail.")

    club_id = payload.club_id if role in ROLES_A_CLUB else None
    if role in ROLES_A_CLUB and club_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Un compte coach ou club doit être rattaché à un club.",
        )
    await _verifier_club(db, club_id)

    # Mot de passe inutilisable : personne ne le connaît, la connexion reste
    # impossible tant que l'activation n'a pas eu lieu.
    user = User(
        email=email,
        mot_de_passe_hash=hash_password(hash_password(f"inutilisable-{email}")),
        role=role,
        nom_complet=payload.nom_complet.strip(),
        club_id=club_id,
        est_actif=True,
    )
    raw, jeton_hash, echeance = _nouveau_jeton_activation()
    user.jeton_activation_hash = jeton_hash
    user.jeton_activation_expire = echeance
    db.add(user)
    await db.flush()
    await log_audit(
        db, "users", user.id, ActionAudit.INSERT, current_user.id, None,
        {
            "email": user.email,
            "role": _role_value(user.role),
            "club_id": user.club_id,
            "nom_complet": user.nom_complet,
            "mot_de_passe": "aucun - activation par code",
        },
    )
    await db.commit()
    await db.refresh(user)
    return CreationCompteOut(utilisateur=_out(user), jeton_activation=raw)


@router.post("/{user_id}/reinitialiser", response_model=CreationCompteOut)
async def reinitialiser_mot_de_passe(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN)),
):
    """L'admin déclenche la réinitialisation ; il ne voit JAMAIS le nouveau
    mot de passe : il transmet un code à usage unique, et la personne choisit
    elle-même son mot de passe. Toutes les sessions sont révoquées."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compte introuvable.")
    raw, jeton_hash, echeance = _nouveau_jeton_activation()
    user.jeton_activation_hash = jeton_hash
    user.jeton_activation_expire = echeance
    # L'ancien mot de passe meurt immédiatement : personne ne peut plus se
    # connecter avant que la personne ait choisi le nouveau via son code.
    user.mot_de_passe_hash = hash_password(secrets.token_urlsafe(32))
    await _revoquer_sessions(db, user.id)
    await log_audit(
        db, "users", user.id, ActionAudit.UPDATE, current_user.id,
        None, {"reinitialisation": "code généré", "sessions": "révoquées"},
    )
    await db.commit()
    await db.refresh(user)
    return CreationCompteOut(utilisateur=_out(user), jeton_activation=raw)


@router.patch("/{user_id}", response_model=AdminUserOut)
async def modifier_utilisateur(
    user_id: int,
    payload: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN)),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compte introuvable.")
    if user.id == current_user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Votre propre compte admin ne se modifie pas ici.",
        )
    data = payload.model_dump(exclude_unset=True)
    if "role" in data:
        role = data["role"] if isinstance(data["role"], RoleUtilisateur) else RoleUtilisateur(str(data["role"]))
        if _role_value(user.role) == "admin" or role not in ROLES_ATTRIBUABLES:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Rôle non modifiable ici : coach, club, collecteur ou organisateur.",
            )
        data["role"] = role
    if "club_id" in data:
        await _verifier_club(db, data["club_id"])
    if "nom_complet" in data and data["nom_complet"] is not None:
        data["nom_complet"] = str(data["nom_complet"]).strip()

    avant = {k: (_role_value(getattr(user, k)) if k == "role" else getattr(user, k)) for k in data}
    for champ, valeur in data.items():
        setattr(user, champ, valeur)
    role_final = _role_value(user.role)
    if role_final in ("coach", "club_manager") and user.club_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Un compte coach ou club doit être rattaché à un club.",
        )
    apres = {k: (_role_value(v) if k == "role" else v) for k, v in data.items()}
    await log_audit(db, "users", user.id, ActionAudit.UPDATE, current_user.id, avant, apres)
    await db.commit()
    await db.refresh(user)
    return _out(user)
