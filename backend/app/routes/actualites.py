"""Actualités et annonces officielles.

Le public peut lire et aimer les publications. Seuls ADMIN et ORGANISATEUR
peuvent créer, modifier, publier, archiver, gérer les images et désigner
l'Homme du match. La portée d'un organisateur est vérifiée via la table
organisateur_competitions existante.
"""
from datetime import datetime, timezone
import hashlib

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.rbac import require_roles, verifier_organisateur_de_competition
from app.database import get_db
from app.models.actualite import Actualite, ActualiteImage, ActualiteLecture, ActualiteLike, HommeMatch
from app.models.club import Club
from app.models.competition import Competition, Saison
from app.models.enums import ActionAudit, CategorieActualite, RoleUtilisateur, StatutActualite, StatutMatch
from app.models.joueur import Joueur
from app.models.match import Match, MatchParticipation
from app.models.user import User
from app.schemas.actualite import (
    ActualiteCreate,
    ActualiteDetailOut,
    ActualiteImageOut,
    ActualiteJoueurOut,
    ActualiteListOut,
    ActualiteMatchOut,
    ActualiteUpdate,
    HommeMatchCreate,
    HommeMatchOut,
    LectureOut,
    LikeOut,
    LikePayload,
)
from app.services.audit import log_audit
from app.services.stockage_actualite import ActualiteDepotRefus, uploader_image_actualite, url_publique

router = APIRouter(prefix="/actualites", tags=["Actualités"])
EDITOR_ROLES = (RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)


def _value(value):
    return value.value if hasattr(value, "value") else value


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _options():
    return (
        selectinload(Actualite.images),
        selectinload(Actualite.auteur),
        selectinload(Actualite.competition),
        selectinload(Actualite.saison),
        selectinload(Actualite.club),
        selectinload(Actualite.joueur).selectinload(Joueur.photo_actuelle_rel),
    )


async def _load_actualite(actualite_id: int, db: AsyncSession) -> Actualite:
    result = await db.execute(select(Actualite).where(Actualite.id == actualite_id).options(*_options()))
    actualite = result.scalar_one_or_none()
    if actualite is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Actualité introuvable.")
    return actualite


async def _like_count(actualite_id: int, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(ActualiteLike.id)).where(ActualiteLike.actualite_id == actualite_id)
    )
    return int(result.scalar() or 0)


async def _like_state(actualite_id: int, client_token: str | None, db: AsyncSession) -> bool:
    if not client_token:
        return False
    result = await db.execute(
        select(ActualiteLike.id).where(
            ActualiteLike.actualite_id == actualite_id,
            ActualiteLike.token_hash == _token_hash(client_token),
        )
    )
    return result.scalar_one_or_none() is not None


async def _lecture_state(actualite_id: int, client_token: str | None, db: AsyncSession) -> bool:
    if not client_token:
        return False
    result = await db.execute(
        select(ActualiteLecture.id).where(
            ActualiteLecture.actualite_id == actualite_id,
            ActualiteLecture.token_hash == _token_hash(client_token),
        )
    )
    return result.scalar_one_or_none() is not None


async def _marquer_lue(actualite_id: int, client_token: str | None, db: AsyncSession) -> None:
    if not client_token:
        return
    token_hash = _token_hash(client_token)
    deja_lue = await db.execute(
        select(ActualiteLecture.id).where(
            ActualiteLecture.actualite_id == actualite_id,
            ActualiteLecture.token_hash == token_hash,
        )
    )
    if deja_lue.scalar_one_or_none() is not None:
        return
    db.add(ActualiteLecture(actualite_id=actualite_id, token_hash=token_hash))
    try:
        await db.commit()
    except IntegrityError:
        # Deux onglets peuvent ouvrir la même actualité simultanément.
        await db.rollback()


async def _match_out(match_: Match, db: AsyncSession) -> ActualiteMatchOut:
    home = await db.get(Club, match_.equipe_domicile_id) if match_.equipe_domicile_id else None
    away = await db.get(Club, match_.equipe_exterieur_id) if match_.equipe_exterieur_id else None
    return ActualiteMatchOut(
        id=match_.id,
        journee=match_.journee,
        date_heure=match_.date_heure,
        stade=match_.stade,
        equipe_domicile_id=match_.equipe_domicile_id,
        equipe_domicile_nom=home.nom if home else None,
        equipe_exterieur_id=match_.equipe_exterieur_id,
        equipe_exterieur_nom=away.nom if away else None,
        score_domicile=match_.score_domicile,
        score_exterieur=match_.score_exterieur,
        statut=_value(match_.statut),
        groupe=match_.groupe,
    )


async def _homme_out(homme: HommeMatch | None, db: AsyncSession) -> HommeMatchOut | None:
    if homme is None:
        return None
    joueur = homme.joueur or await db.get(Joueur, homme.joueur_id)
    club = homme.club or await db.get(Club, homme.club_id)
    return HommeMatchOut(
        id=homme.id,
        match_id=homme.match_id,
        joueur_id=homme.joueur_id,
        joueur_nom=joueur.nom_complet if joueur else "Joueur",
        club_id=homme.club_id,
        club_nom=club.nom if club else "Équipe",
        joueur_photo_url=joueur.photo_url if joueur else None,
        designe_par_id=homme.designe_par_id,
        designe_at=homme.designe_at,
    )


async def _serialize_list(
    actualite: Actualite,
    db: AsyncSession,
    client_token: str | None = None,
) -> ActualiteListOut:
    images = actualite.images or []
    principale = next((image for image in images if image.principale), images[0] if images else None)
    return ActualiteListOut(
        id=actualite.id,
        titre=actualite.titre,
        categorie=actualite.categorie,
        statut=actualite.statut,
        mise_en_avant=actualite.mise_en_avant,
        image_principale_url=url_publique(principale.storage_key) if principale else None,
        date_creation=actualite.date_creation,
        date_publication=actualite.date_publication,
        competition_id=actualite.competition_id,
        competition_nom=actualite.competition.nom if actualite.competition else None,
        saison_id=actualite.saison_id,
        saison_nom=actualite.saison.nom if actualite.saison else None,
        match_id=actualite.match_id,
        joueur_id=actualite.joueur_id,
        joueur_nom=actualite.joueur.nom_complet if actualite.joueur else None,
        like_count=await _like_count(actualite.id, db),
        lu=await _lecture_state(actualite.id, client_token, db),
    )


async def _serialize_detail(actualite: Actualite, db: AsyncSession, client_token: str | None = None) -> ActualiteDetailOut:
    base = await _serialize_list(actualite, db, client_token)
    images = [
        ActualiteImageOut(
            id=image.id,
            url=url_publique(image.storage_key),
            mime_type=image.mime_type,
            file_size=image.file_size,
            ordre=image.ordre,
            principale=image.principale,
            telechargement_autorise=actualite.telechargement_autorise,
        )
        for image in (actualite.images or [])
    ]
    match_out = None
    if actualite.match_id:
        match_ = await db.get(Match, actualite.match_id)
        if match_:
            match_out = await _match_out(match_, db)
    joueur_out = None
    if actualite.joueur:
        joueur_club = await db.get(Club, actualite.joueur.club_actuel_id) if actualite.joueur.club_actuel_id else None
        joueur_out = ActualiteJoueurOut(
            id=actualite.joueur.id,
            nom_complet=actualite.joueur.nom_complet,
            club_id=actualite.joueur.club_actuel_id,
            club_nom=joueur_club.nom if joueur_club else None,
            photo_url=actualite.joueur.photo_url,
        )
    homme = None
    if actualite.match_id:
        hm = await db.execute(
            select(HommeMatch)
            .where(HommeMatch.match_id == actualite.match_id)
            .options(selectinload(HommeMatch.joueur).selectinload(Joueur.photo_actuelle_rel), selectinload(HommeMatch.club))
        )
        homme = await _homme_out(hm.scalar_one_or_none(), db)
    return ActualiteDetailOut(
        **base.model_dump(),
        texte=actualite.texte,
        auteur_id=actualite.auteur_id,
        auteur_nom=actualite.auteur.nom_complet if actualite.auteur else None,
        journee=actualite.journee,
        club_id=actualite.club_id,
        club_nom=actualite.club.nom if actualite.club else None,
        telechargement_autorise=actualite.telechargement_autorise,
        images=images,
        match=match_out,
        joueur=joueur_out,
        homme_match=homme,
        liked=await _like_state(actualite.id, client_token, db),
    )


async def _resolve_context(
    db: AsyncSession,
    current_user: User,
    competition_id: int | None,
    saison_id: int | None,
    match_id: int | None,
    club_id: int | None,
    joueur_id: int | None,
) -> tuple[int | None, int | None, int | None, int | None, int | None]:
    """Valide les relations et retourne le contexte normalisé."""
    comp_id = competition_id
    season_id = saison_id
    match = None
    if comp_id is not None:
        if await db.get(Competition, comp_id) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Compétition introuvable.")
    if season_id is not None:
        season = await db.get(Saison, season_id)
        if season is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Édition introuvable.")
        if comp_id is not None and season.competition_id != comp_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "L'édition ne correspond pas à la compétition.")
        comp_id = season.competition_id
    if match_id is not None:
        match = await db.get(Match, match_id)
        if match is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
        season = await db.get(Saison, match.saison_id)
        if season is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Le match n'est pas relié à une édition valide.")
        if season_id is not None and season_id != season.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Le match ne correspond pas à l'édition.")
        if comp_id is not None and comp_id != season.competition_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Le match ne correspond pas à la compétition.")
        season_id = season.id
        comp_id = season.competition_id
    if club_id is not None and await db.get(Club, club_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Équipe associée introuvable.")
    if joueur_id is not None and await db.get(Joueur, joueur_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Joueur associé introuvable.")
    if match is not None and club_id is not None:
        if club_id not in (match.equipe_domicile_id, match.equipe_exterieur_id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "L'équipe ne participe pas à ce match.")
    if match is not None and joueur_id is not None:
        joueur = await db.get(Joueur, joueur_id)
        participe = await db.execute(
            select(MatchParticipation.id).where(
                MatchParticipation.match_id == match.id,
                MatchParticipation.joueur_id == joueur_id,
            ).limit(1)
        )
        if joueur and joueur.club_actuel_id not in (match.equipe_domicile_id, match.equipe_exterieur_id) and participe.scalar_one_or_none() is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Le joueur n'est pas rattaché à une équipe de ce match.")
    if current_user.role == RoleUtilisateur.ORGANISATEUR:
        if comp_id is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Un organisateur doit rattacher l'actualité à sa compétition.")
        await verifier_organisateur_de_competition(comp_id, current_user, db)
    return comp_id, season_id, match_id, club_id, joueur_id


async def _can_manage(actualite: Actualite, current_user: User, db: AsyncSession) -> None:
    if current_user.role == RoleUtilisateur.ADMIN:
        return
    if current_user.role != RoleUtilisateur.ORGANISATEUR or actualite.competition_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cette actualité n'est pas dans votre périmètre.")
    await verifier_organisateur_de_competition(actualite.competition_id, current_user, db)


@router.get("", response_model=list[ActualiteListOut])
async def lister_actualites_publiques(
    categorie: CategorieActualite | None = None,
    competition_id: int | None = None,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    client_token: str | None = None,
):
    query = (
        select(Actualite)
        .where(Actualite.statut == StatutActualite.PUBLIE)
        .options(*_options())
        .order_by(Actualite.mise_en_avant.desc(), Actualite.date_publication.desc(), Actualite.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if categorie is not None:
        query = query.where(Actualite.categorie == categorie)
    if competition_id is not None:
        query = query.where(Actualite.competition_id == competition_id)
    result = await db.execute(query)
    return [await _serialize_list(item, db, client_token) for item in result.scalars().all()]


@router.get("/gestion", response_model=list[ActualiteDetailOut])
async def lister_actualites_gestion(
    statut: StatutActualite | None = None,
    competition_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*EDITOR_ROLES)),
):
    query = select(Actualite).options(*_options()).order_by(Actualite.date_creation.desc())
    if statut is not None:
        query = query.where(Actualite.statut == statut)
    if competition_id is not None:
        await verifier_organisateur_de_competition(competition_id, current_user, db)
        query = query.where(Actualite.competition_id == competition_id)
    elif current_user.role == RoleUtilisateur.ORGANISATEUR:
        from app.models.competition import OrganisateurCompetition
        allowed = select(OrganisateurCompetition.competition_id).where(
            OrganisateurCompetition.user_id == current_user.id
        )
        query = query.where(Actualite.competition_id.in_(allowed))
    result = await db.execute(query.limit(100))
    return [await _serialize_detail(item, db) for item in result.scalars().all()]


@router.get("/gestion/{actualite_id}", response_model=ActualiteDetailOut)
async def detail_actualite_gestion(
    actualite_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*EDITOR_ROLES)),
):
    actualite = await _load_actualite(actualite_id, db)
    await _can_manage(actualite, current_user, db)
    return await _serialize_detail(actualite, db)


@router.get("/gestion/{actualite_id}/previsualiser", response_model=ActualiteDetailOut)
async def previsualiser_actualite(
    actualite_id: int,
    client_token: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*EDITOR_ROLES)),
):
    actualite = await _load_actualite(actualite_id, db)
    await _can_manage(actualite, current_user, db)
    return await _serialize_detail(actualite, db, client_token)


@router.post("", response_model=ActualiteDetailOut, status_code=status.HTTP_201_CREATED)
async def creer_actualite(
    payload: ActualiteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*EDITOR_ROLES)),
):
    comp_id, season_id, match_id, club_id, joueur_id = await _resolve_context(
        db, current_user, payload.competition_id, payload.saison_id, payload.match_id, payload.club_id, payload.joueur_id
    )
    actualite = Actualite(
        titre=payload.titre,
        categorie=payload.categorie,
        texte=payload.texte,
        statut=StatutActualite.BROUILLON,
        telechargement_autorise=payload.telechargement_autorise,
        mise_en_avant=payload.mise_en_avant,
        auteur_id=current_user.id,
        competition_id=comp_id,
        saison_id=season_id,
        journee=payload.journee,
        match_id=match_id,
        club_id=club_id,
        joueur_id=joueur_id,
    )
    db.add(actualite)
    await db.flush()
    await log_audit(db, "actualites", actualite.id, ActionAudit.INSERT, current_user.id, None, {
        "titre": actualite.titre,
        "categorie": _value(actualite.categorie),
        "statut": StatutActualite.BROUILLON.value,
        "mise_en_avant": actualite.mise_en_avant,
        "competition_id": comp_id,
        "match_id": match_id,
    })
    await db.commit()
    actualite = await _load_actualite(actualite.id, db)
    return await _serialize_detail(actualite, db)


@router.put("/{actualite_id}", response_model=ActualiteDetailOut)
async def modifier_actualite(
    actualite_id: int,
    payload: ActualiteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*EDITOR_ROLES)),
):
    actualite = await _load_actualite(actualite_id, db)
    await _can_manage(actualite, current_user, db)
    data = payload.model_dump(exclude_unset=True)
    comp_id, season_id, match_id, club_id, joueur_id = await _resolve_context(
        db,
        current_user,
        data.get("competition_id", actualite.competition_id),
        data.get("saison_id", actualite.saison_id),
        data.get("match_id", actualite.match_id),
        data.get("club_id", actualite.club_id),
        data.get("joueur_id", actualite.joueur_id),
    )
    old = {key: getattr(actualite, key) for key in data if hasattr(actualite, key)}
    for key in ("titre", "categorie", "texte", "telechargement_autorise", "mise_en_avant", "journee"):
        if key in data:
            setattr(actualite, key, data[key])
    actualite.competition_id = comp_id
    actualite.saison_id = season_id
    actualite.match_id = match_id
    actualite.club_id = club_id
    actualite.joueur_id = joueur_id
    await log_audit(db, "actualites", actualite.id, ActionAudit.UPDATE, current_user.id, old, {
        "titre": actualite.titre,
        "categorie": _value(actualite.categorie),
        "mise_en_avant": actualite.mise_en_avant,
        "competition_id": comp_id,
        "match_id": match_id,
    })
    await db.commit()
    actualite = await _load_actualite(actualite.id, db)
    return await _serialize_detail(actualite, db)


@router.post("/{actualite_id}/publier", response_model=ActualiteDetailOut)
async def publier_actualite(
    actualite_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*EDITOR_ROLES)),
):
    actualite = await _load_actualite(actualite_id, db)
    await _can_manage(actualite, current_user, db)
    if actualite.statut == StatutActualite.ARCHIVE:
        raise HTTPException(status.HTTP_409_CONFLICT, "Une actualité archivée doit d'abord être modifiée.")
    actualite.statut = StatutActualite.PUBLIE
    actualite.date_publication = actualite.date_publication or datetime.now(timezone.utc)
    await log_audit(db, "actualites", actualite.id, ActionAudit.VALIDATE, current_user.id, {"statut": "brouillon"}, {"statut": "publie"})
    await db.commit()
    actualite = await _load_actualite(actualite.id, db)
    return await _serialize_detail(actualite, db)


@router.post("/{actualite_id}/archiver", response_model=ActualiteDetailOut)
async def archiver_actualite(
    actualite_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*EDITOR_ROLES)),
):
    actualite = await _load_actualite(actualite_id, db)
    await _can_manage(actualite, current_user, db)
    ancien = _value(actualite.statut)
    actualite.statut = StatutActualite.ARCHIVE
    await log_audit(db, "actualites", actualite.id, ActionAudit.UPDATE, current_user.id, {"statut": ancien}, {"statut": "archive"})
    await db.commit()
    actualite = await _load_actualite(actualite.id, db)
    return await _serialize_detail(actualite, db)


@router.post("/{actualite_id}/images", response_model=ActualiteImageOut, status_code=status.HTTP_201_CREATED)
async def ajouter_image_actualite(
    actualite_id: int,
    file: UploadFile = File(...),
    principale: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*EDITOR_ROLES)),
):
    actualite = await _load_actualite(actualite_id, db)
    await _can_manage(actualite, current_user, db)
    data = await file.read()
    try:
        key, taille = await uploader_image_actualite(actualite_id, file.content_type or "", data)
    except ActualiteDepotRefus as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    ordre_result = await db.execute(
        select(func.coalesce(func.max(ActualiteImage.ordre), -1)).where(ActualiteImage.actualite_id == actualite_id)
    )
    ordre = int(ordre_result.scalar() or -1) + 1
    if not actualite.images:
        principale = True
    if principale:
        images = await db.execute(select(ActualiteImage).where(ActualiteImage.actualite_id == actualite_id))
        for image in images.scalars().all():
            image.principale = False
    image = ActualiteImage(
        actualite_id=actualite_id,
        storage_key=key,
        mime_type=file.content_type,
        file_size=taille,
        ordre=ordre,
        principale=principale,
        uploaded_by=current_user.id,
    )
    db.add(image)
    await db.flush()
    await log_audit(db, "actualite_images", image.id, ActionAudit.INSERT, current_user.id, None, {"actualite_id": actualite_id, "principale": principale})
    await db.commit()
    return ActualiteImageOut(
        id=image.id,
        url=url_publique(image.storage_key),
        mime_type=image.mime_type,
        file_size=image.file_size,
        ordre=image.ordre,
        principale=image.principale,
        telechargement_autorise=actualite.telechargement_autorise,
    )


@router.delete("/{actualite_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def supprimer_image_actualite(
    actualite_id: int,
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*EDITOR_ROLES)),
):
    actualite = await _load_actualite(actualite_id, db)
    await _can_manage(actualite, current_user, db)
    image = await db.get(ActualiteImage, image_id)
    if image is None or image.actualite_id != actualite_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image introuvable.")
    if actualite.statut == StatutActualite.PUBLIE:
        raise HTTPException(status.HTTP_409_CONFLICT, "Une image publiée est conservée dans l'historique.")
    await log_audit(db, "actualite_images", image.id, ActionAudit.DELETE, current_user.id, {"actualite_id": actualite_id}, None)
    await db.delete(image)
    await db.commit()
    return None


@router.post("/{actualite_id}/like", response_model=LikeOut)
async def aimer_actualite(
    actualite_id: int,
    payload: LikePayload,
    db: AsyncSession = Depends(get_db),
):
    actualite = await db.get(Actualite, actualite_id)
    if actualite is None or actualite.statut != StatutActualite.PUBLIE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Actualité introuvable.")
    token_hash = _token_hash(payload.client_token)
    existing = await db.execute(
        select(ActualiteLike).where(
            ActualiteLike.actualite_id == actualite_id,
            ActualiteLike.token_hash == token_hash,
        )
    )
    like = existing.scalar_one_or_none()
    if like is None:
        db.add(ActualiteLike(actualite_id=actualite_id, token_hash=token_hash))
        liked = True
    else:
        await db.delete(like)
        liked = False
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        liked = True
    return LikeOut(actualite_id=actualite_id, liked=liked, like_count=await _like_count(actualite_id, db))


@router.post("/matchs/{match_id}/homme-du-match", response_model=HommeMatchOut)
async def designer_homme_du_match(
    match_id: int,
    payload: HommeMatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*EDITOR_ROLES)),
):
    match_ = await db.get(Match, match_id)
    if match_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    season = await db.get(Saison, match_.saison_id)
    if season is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Édition du match introuvable.")
    await verifier_organisateur_de_competition(season.competition_id, current_user, db)
    statut = _value(match_.statut)
    if statut not in (StatutMatch.TERMINE.value, StatutMatch.VALIDE.value, "termine", "valide"):
        raise HTTPException(status.HTTP_409_CONFLICT, "L'Homme du match se désigne après la fin du match.")
    joueur = await db.get(Joueur, payload.joueur_id)
    if joueur is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Joueur introuvable.")
    participation = await db.execute(
        select(MatchParticipation.id).where(
            MatchParticipation.match_id == match_id,
            MatchParticipation.joueur_id == payload.joueur_id,
        ).limit(1)
    )
    if joueur.club_actuel_id not in (match_.equipe_domicile_id, match_.equipe_exterieur_id) and participation.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ce joueur ne fait pas partie de ce match.")
    club_id = joueur.club_actuel_id
    if club_id not in (match_.equipe_domicile_id, match_.equipe_exterieur_id):
        participation_row = await db.execute(
            select(MatchParticipation.club_id).where(
                MatchParticipation.match_id == match_id,
                MatchParticipation.joueur_id == payload.joueur_id,
            ).limit(1)
        )
        club_id = participation_row.scalar_one_or_none()
    if club_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Impossible de déterminer l'équipe du joueur.")
    existing = await db.execute(select(HommeMatch).where(HommeMatch.match_id == match_id))
    homme = existing.scalar_one_or_none()
    old = None
    if homme:
        old = {"joueur_id": homme.joueur_id, "club_id": homme.club_id}
        homme.joueur_id = payload.joueur_id
        homme.club_id = club_id
        homme.designe_par_id = current_user.id
        homme.designe_at = datetime.now(timezone.utc)
    else:
        homme = HommeMatch(match_id=match_id, joueur_id=payload.joueur_id, club_id=club_id, designe_par_id=current_user.id)
        db.add(homme)
    await db.flush()
    await log_audit(db, "hommes_match", homme.id, ActionAudit.UPDATE if old else ActionAudit.INSERT, current_user.id, old, {"joueur_id": payload.joueur_id, "club_id": club_id})
    await db.commit()
    result = await db.execute(
        select(HommeMatch).where(HommeMatch.id == homme.id).options(selectinload(HommeMatch.joueur).selectinload(Joueur.photo_actuelle_rel), selectinload(HommeMatch.club))
    )
    return await _homme_out(result.scalar_one(), db)


@router.post("/{actualite_id}/lecture", response_model=LectureOut)
async def marquer_actualite_lue(
    actualite_id: int,
    client_token: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    actualite = await _load_actualite(actualite_id, db)
    if actualite.statut != StatutActualite.PUBLIE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Actualité introuvable.")
    await _marquer_lue(actualite.id, client_token, db)
    return LectureOut(actualite_id=actualite.id, lu=await _lecture_state(actualite.id, client_token, db))


@router.get("/{actualite_id}", response_model=ActualiteDetailOut)
async def detail_actualite_publique(
    actualite_id: int,
    client_token: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    actualite = await _load_actualite(actualite_id, db)
    if actualite.statut != StatutActualite.PUBLIE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Actualité introuvable.")
    return await _serialize_detail(actualite, db, client_token)
