from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.rbac import require_roles, verifier_organisateur_de_competition, verifier_organisateur_du_match
from app.database import get_db
from app.models.competition import Saison
from app.models.enums import ActionAudit, EquipeConcernee, RoleUtilisateur, StatutMatch
from app.models.match import Match, MatchParticipation
from app.models.user import User
from app.schemas.match import MatchCreate, MatchOut, ParticipationCreate, ParticipationOut
from app.services.audit import log_audit
from app.services.validation import valider_match

router = APIRouter(prefix="/matchs", tags=["Matchs"])


@router.get("", response_model=list[MatchOut])
async def lister_matchs(
    db: AsyncSession = Depends(get_db),
    saison_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """
    Public : uniquement les matchs `valide` (§5.3). Les autres statuts
    ne sont visibles que via les routes protégées (organisateur).
    """
    query = select(Match).where(Match.statut == StatutMatch.VALIDE)
    if saison_id:
        query = query.where(Match.saison_id == saison_id)
    result = await db.execute(query.order_by(Match.date_heure.desc()).limit(min(limit, 100)).offset(offset))
    return result.scalars().all()


@router.get("/gestion", response_model=list[MatchOut])
async def lister_matchs_gestion(
    db: AsyncSession = Depends(get_db),
    saison_id: int | None = None,
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
    limit: int = 50,
    offset: int = 0,
):
    """Tous les statuts — réservé organisateur / admin (Phase 5)."""
    query = select(Match)
    if saison_id:
        query = query.where(Match.saison_id == saison_id)
    result = await db.execute(query.order_by(Match.date_heure.desc()).limit(min(limit, 100)).offset(offset))
    return result.scalars().all()


@router.get("/gestion/{match_id}", response_model=MatchOut)
async def detail_match_gestion(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    match_ = await verifier_organisateur_du_match(match_id, current_user, db)
    return match_


@router.get("/{match_id}", response_model=MatchOut)
async def detail_match(match_id: int, db: AsyncSession = Depends(get_db)):
    match_ = await db.get(Match, match_id)
    if match_ is None or match_.statut != StatutMatch.VALIDE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable ou non publié.")
    return match_


@router.post("", response_model=MatchOut, status_code=status.HTTP_201_CREATED)
async def creer_match(
    payload: MatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    saison = await db.get(Saison, payload.saison_id)
    if saison is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saison introuvable.")
    await verifier_organisateur_de_competition(saison.competition_id, current_user, db)

    match_ = Match(**payload.model_dump())
    db.add(match_)
    await db.flush()
    await log_audit(db, "matchs", match_.id, ActionAudit.INSERT, current_user.id, None, {"saison_id": payload.saison_id})
    await db.commit()
    await db.refresh(match_)
    return match_


@router.put("/{match_id}/statut", response_model=MatchOut)
async def changer_statut_match(
    match_id: int,
    nouveau_statut: StatutMatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    """
    Cycle de vie (Phase 1) : programme -> en_cours -> termine -> valide,
    ou conteste à tout moment. La transition vers 'valide' passe
    obligatoirement par la route dédiée /matchs/{id}/valider (elle seule
    vérifie qu'aucun événement n'est en attente et verrouille le match).
    """
    match_ = await verifier_organisateur_du_match(match_id, current_user, db)
    if match_.locked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ce match est verrouillé.")
    if nouveau_statut == StatutMatch.VALIDE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Utilisez POST /matchs/{id}/valider pour valider un match (vérifications supplémentaires requises).",
        )
    old_statut = match_.statut.value if hasattr(match_.statut, "value") else match_.statut
    match_.statut = nouveau_statut
    await log_audit(db, "matchs", match_.id, ActionAudit.UPDATE, current_user.id, {"statut": old_statut}, {"statut": nouveau_statut.value})
    await db.commit()
    await db.refresh(match_)
    return match_


@router.post("/{match_id}/valider", response_model=MatchOut)
async def valider_match_route(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    await verifier_organisateur_du_match(match_id, current_user, db)
    match_ = await valider_match(db, match_id, current_user.id)
    await db.commit()
    await db.refresh(match_)
    return match_


@router.post("/{match_id}/forfait", response_model=MatchOut)
async def declarer_forfait(
    match_id: int,
    equipe_forfait: EquipeConcernee,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    """Forfait tracé explicitement (§3.5, corrigé Phase 0) - jamais un simple score 3-0 muet."""
    match_ = await verifier_organisateur_du_match(match_id, current_user, db)
    if match_.locked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ce match est verrouillé.")
    match_.forfait = True
    match_.forfait_equipe = equipe_forfait
    if equipe_forfait == EquipeConcernee.DOMICILE:
        match_.score_domicile, match_.score_exterieur = 0, 3
    else:
        match_.score_domicile, match_.score_exterieur = 3, 0
    match_.statut = StatutMatch.TERMINE
    await log_audit(db, "matchs", match_.id, ActionAudit.UPDATE, current_user.id, None, {"forfait": True, "forfait_equipe": equipe_forfait.value})
    await db.commit()
    await db.refresh(match_)
    return match_


@router.post("/{match_id}/participations", response_model=ParticipationOut, status_code=status.HTTP_201_CREATED)
async def ajouter_participation(
    match_id: int,
    payload: ParticipationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    match_ = await verifier_organisateur_du_match(match_id, current_user, db)
    if match_.locked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ce match est verrouillé.")
    participation = MatchParticipation(match_id=match_id, **payload.model_dump())
    db.add(participation)
    await db.commit()
    await db.refresh(participation)
    return participation


@router.get("/{match_id}/participations", response_model=list[ParticipationOut])
async def lister_participations(match_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MatchParticipation).where(MatchParticipation.match_id == match_id))
    return result.scalars().all()
