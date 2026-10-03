from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import require_roles, verifier_organisateur_de_competition, verifier_organisateur_du_match
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


async def _out(document: DocumentOfficiel) -> DocumentOut:
    return DocumentOut.model_validate(document).model_copy(update={"url": await document_url(document)})


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
async def documents_match(match_id: int, db: AsyncSession = Depends(get_db)):
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
async def documents_joueur(joueur_id: int, saison_id: int | None = None, db: AsyncSession = Depends(get_db)):
    query = select(DocumentOfficiel).where(DocumentOfficiel.type_document == "joueur", DocumentOfficiel.scope_id == joueur_id, DocumentOfficiel.statut == "publie")
    if saison_id is not None:
        query = query.where(DocumentOfficiel.saison_id == saison_id)
    rows = (await db.execute(query.order_by(DocumentOfficiel.created_at.desc()))).scalars().all()
    return [await _out(row) for row in rows]


@router.get("/{document_id}/telecharger")
async def telecharger_document(document_id: int, db: AsyncSession = Depends(get_db)):
    document = await db.get(DocumentOfficiel, document_id)
    if document is None or document.statut != "publie":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document officiel introuvable.")
    url = await document_url(document)
    if url:
        return RedirectResponse(url)
    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Document temporairement indisponible.")
