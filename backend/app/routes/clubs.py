from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import require_roles
from app.database import get_db
from app.models.club import Club
from app.models.enums import ActionAudit, RoleUtilisateur
from app.models.user import User
from app.schemas.competition import ClubCreate, ClubOut
from app.services.audit import log_audit

router = APIRouter(prefix="/clubs", tags=["Clubs"])


@router.get("", response_model=list[ClubOut])
async def lister_clubs(db: AsyncSession = Depends(get_db), limit: int = 20, offset: int = 0):
    result = await db.execute(select(Club).limit(min(limit, 100)).offset(offset))
    return result.scalars().all()


@router.get("/{club_id}", response_model=ClubOut)
async def detail_club(club_id: int, db: AsyncSession = Depends(get_db)):
    club = await db.get(Club, club_id)
    if club is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Club introuvable.")
    return club


@router.post("", response_model=ClubOut, status_code=status.HTTP_201_CREATED)
async def creer_club(
    payload: ClubCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN)),
):
    club = Club(**payload.model_dump())
    db.add(club)
    await db.flush()
    await log_audit(db, "clubs", club.id, ActionAudit.INSERT, current_user.id, None, payload.model_dump())
    await db.commit()
    await db.refresh(club)
    return club
