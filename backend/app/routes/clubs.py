from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import require_roles
from app.database import get_db
from app.models.club import Club
from app.models.enums import ActionAudit, RoleUtilisateur
from app.models.match import Match
from app.models.user import User
from app.schemas.competition import ClubCreate, ClubOut, ClubUpdate
from app.services.audit import log_audit

router = APIRouter(prefix="/clubs", tags=["Clubs"])


async def _coach_noms(db: AsyncSession, club_ids: list[int]) -> dict[int, str]:
    ids = [i for i in club_ids if i]
    if not ids:
        return {}
    result = await db.execute(
        select(User.club_id, User.nom_complet).where(
            User.role == RoleUtilisateur.COACH,
            User.est_actif.is_(True),
            User.club_id.in_(ids),
            User.nom_complet.is_not(None),
        )
    )
    out: dict[int, str] = {}
    for club_id, nom in result.all():
        if club_id and nom and club_id not in out:
            out[club_id] = nom
    return out


def _club_out(club: Club, coach_nom: str | None) -> ClubOut:
    return ClubOut.model_validate(club).model_copy(update={"coach_nom": coach_nom})


@router.get("", response_model=list[ClubOut])
async def lister_clubs(db: AsyncSession = Depends(get_db), limit: int = 20, offset: int = 0):
    result = await db.execute(select(Club).limit(min(limit, 100)).offset(offset))
    clubs = result.scalars().all()
    noms = await _coach_noms(db, [c.id for c in clubs])
    return [_club_out(c, noms.get(c.id)) for c in clubs]


@router.get("/{club_id}", response_model=ClubOut)
async def detail_club(club_id: int, db: AsyncSession = Depends(get_db)):
    club = await db.get(Club, club_id)
    if club is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Club introuvable.")
    noms = await _coach_noms(db, [club_id])
    return _club_out(club, noms.get(club_id))


@router.post("", response_model=ClubOut, status_code=status.HTTP_201_CREATED)
async def creer_club(
    payload: ClubCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    club = Club(**payload.model_dump())
    db.add(club)
    await db.flush()
    await log_audit(db, "clubs", club.id, ActionAudit.INSERT, current_user.id, None, payload.model_dump())
    await db.commit()
    await db.refresh(club)
    return club


@router.put("/{club_id}", response_model=ClubOut)
async def modifier_club(
    club_id: int,
    payload: ClubUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    club = await db.get(Club, club_id)
    if club is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Club introuvable.")
    avant = {"nom": club.nom, "ville": club.ville, "stade": club.stade}
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(club, k, v)
    await log_audit(db, "clubs", club.id, ActionAudit.UPDATE, current_user.id, avant, data)
    await db.commit()
    await db.refresh(club)
    return club


@router.delete("/{club_id}", status_code=status.HTTP_204_NO_CONTENT)
async def supprimer_club(
    club_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    club = await db.get(Club, club_id)
    if club is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Club introuvable.")
    joue = await db.execute(
        select(Match.id).where(
            or_(Match.equipe_domicile_id == club_id, Match.equipe_exterieur_id == club_id)
        ).limit(1)
    )
    if joue.scalar_one_or_none() is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Cette équipe a déjà des matchs. On n’efface pas l’historique — désinscrire si besoin.",
        )
    await log_audit(db, "clubs", club.id, ActionAudit.DELETE, current_user.id, {"nom": club.nom}, None)
    await db.delete(club)
    await db.commit()
    return None
