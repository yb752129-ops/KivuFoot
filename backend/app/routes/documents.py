from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import (
    CLUB_ROLES,
    isClubRole,
    require_roles,
    verifier_organisateur_de_competition,
    verifier_organisateur_du_match,
    verifier_scope_club,
)
from app.database import get_db
from app.models.document import DocumentOfficiel
from app.models.joueur import Joueur
from app.models.match import Match
from app.models.competition import Saison
from app.models.enums import RoleUtilisateur
from app.models.user import User
from app.schemas.document import DocumentOut
from app.services.documents_officiels import document_url, generer_document_joueur, generer_document_match

router = APIRouter(prefix="/documents", tags=["Documents officiels"])

DOCUMENT_READ_ROLES = (RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR, *CLUB_ROLES)


async def _out(document: DocumentOfficiel) -> DocumentOut:
    return DocumentOut.model_validate(document).model_copy(update={"url": await document_url(document)})


async def _match_scope(match_id: int, current_user: User, db: AsyncSession) -> Match:
    match_ = await db.get(Match, match_id)
    if match_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    if current_user.role == RoleUtilisateur.ADMIN or current_user.role == RoleUtilisateur.ORGANISATEUR:
        await verifier_organisateur_du_match(match_id, current_user, db)
    elif isClubRole(current_user.role):
        if current_user.club_id not in (match_.equipe_domicile_id, match_.equipe_exterieur_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Vous ne gérez aucune équipe de ce match.")
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Vous n'avez pas accès à ce document.")
    return match_


async def _joueur_scope(
    joueur_id: int,
    saison_id: int | None,
    current_user: User,
    db: AsyncSession,
) -> Joueur:
    joueur = await db.get(Joueur, joueur_id)
    if joueur is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Joueur introuvable.")
    if current_user.role == RoleUtilisateur.ADMIN:
        return joueur
    if isClubRole(current_user.role):
        verifier_scope_club(current_user, joueur.club_actuel_id or -1)
        return joueur
    if current_user.role == RoleUtilisateur.ORGANISATEUR:
        if saison_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "saison_id est requis pour cette consultation.")
        saison = await db.get(Saison, saison_id)
        if saison is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Édition introuvable.")
        await verifier_organisateur_de_competition(saison.competition_id, current_user, db)
        return joueur
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Vous n'avez pas accès à ce document.")


@router.post("/matchs/{match_id}/generer", response_model=DocumentOut)
async def generer_match(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    await verifier_organisateur_du_match(match_id, current_user, db)
    document, _ = await generer_document_match(db, match_id, current_user.id)
    await db.commit()
    await db.refresh(document)
    return await _out(document)


@router.get("/matchs/{match_id}", response_model=list[DocumentOut])
async def documents_match(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*DOCUMENT_READ_ROLES)),
):
    await _match_scope(match_id, current_user, db)
    rows = (
        await db.execute(
            select(DocumentOfficiel)
            .where(DocumentOfficiel.type_document == "match", DocumentOfficiel.scope_id == match_id)
            .order_by(DocumentOfficiel.version.desc(), DocumentOfficiel.id.desc())
        )
    ).scalars().all()
    return [await _out(row) for row in rows if row.statut == "publie"]


@router.post("/joueurs/{joueur_id}/generer", response_model=DocumentOut)
async def generer_joueur(
    joueur_id: int,
    saison_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    saison = await db.get(Saison, saison_id)
    if saison is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Édition introuvable.")
    await verifier_organisateur_de_competition(saison.competition_id, current_user, db)
    document, _ = await generer_document_joueur(db, joueur_id, saison_id, current_user.id)
    await db.commit()
    await db.refresh(document)
    return await _out(document)


@router.get("/joueurs/{joueur_id}", response_model=list[DocumentOut])
async def documents_joueur(
    joueur_id: int,
    saison_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*DOCUMENT_READ_ROLES)),
):
    await _joueur_scope(joueur_id, saison_id, current_user, db)
    query = select(DocumentOfficiel).where(
        DocumentOfficiel.type_document == "joueur",
        DocumentOfficiel.scope_id == joueur_id,
        DocumentOfficiel.statut == "publie",
    )
    if saison_id is not None:
        query = query.where(DocumentOfficiel.saison_id == saison_id)
    rows = (await db.execute(query.order_by(DocumentOfficiel.created_at.desc()))).scalars().all()
    return [await _out(row) for row in rows]


@router.get("/{document_id}/telecharger")
async def telecharger_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*DOCUMENT_READ_ROLES)),
):
    document = await db.get(DocumentOfficiel, document_id)
    if document is None or document.statut != "publie":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document officiel introuvable.")
    if document.type_document == "match":
        await _match_scope(document.scope_id, current_user, db)
    elif document.type_document == "joueur":
        await _joueur_scope(document.scope_id, document.saison_id, current_user, db)
    elif current_user.role != RoleUtilisateur.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Vous n'avez pas accès à ce document.")
    url = await document_url(document)
    if url:
        return RedirectResponse(url)
    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Document temporairement indisponible.")
