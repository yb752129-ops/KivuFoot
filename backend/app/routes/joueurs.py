from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.rbac import require_roles, verifier_scope_club
from app.database import get_db
from app.models.enums import ActionAudit, RoleUtilisateur, StatutPhoto, StatutVerificationJoueur
from app.models.joueur import Joueur, JoueurModificationProposee
from app.models.user import User
from app.schemas.joueur import (
    JoueurCreate,
    JoueurDetailOut,
    JoueurMergeRequest,
    JoueurPublicOut,
    JoueurUpdate,
    ModificationProposeeCreate,
    ModificationProposeeOut,
)
from app.services.audit import log_audit
from app.models.photo import Photo
from app.models.staff import Staff
from app.schemas.joueur import JoueurStatutUpdate
from app.schemas.photo import PhotoEnAttenteOut, PhotoOut, PhotoRejet
from app.services.detection_doublons import fusionner_joueurs, rechercher_doublons
from app.services.stockage_photo import DepotRefus, uploader_photo, url_publique
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/joueurs", tags=["Joueurs"])

# Champs qu'un club_manager peut modifier directement, sans passer par le
# workflow de proposition (décision C1) : rien qui affecte l'historique
# sportif ou l'identité du joueur.
CHAMPS_MODIFIABLES_DIRECTEMENT = {"telephone", "email"}
CHAMPS_SENSIBLES = {"club_actuel_id", "date_naissance", "nom_complet", "poste"}


@router.get("", response_model=list[JoueurPublicOut])
async def lister_joueurs(
    db: AsyncSession = Depends(get_db),
    club_id: int | None = None,
    poste: str | None = None,
    nom: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    query = select(Joueur).where(Joueur.fusionne.is_(False), Joueur.anonymise.is_(False))
    if club_id:
        query = query.where(Joueur.club_actuel_id == club_id)
    if poste:
        query = query.where(Joueur.poste == poste)
    if nom:
        query = query.where(Joueur.nom_complet.ilike(f"%{nom}%"))
    query = query.options(selectinload(Joueur.photo_actuelle_rel))
    result = await db.execute(query.limit(min(limit, 100)).offset(offset))
    return result.scalars().all()


@router.get("/propositions", response_model=list[ModificationProposeeOut])
async def lister_propositions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR, RoleUtilisateur.CLUB_MANAGER)
    ),
    joueur_id: int | None = None,
    statut: str | None = "en_attente",
):
    query = select(JoueurModificationProposee)
    if joueur_id:
        query = query.where(JoueurModificationProposee.joueur_id == joueur_id)
    if statut:
        query = query.where(JoueurModificationProposee.statut == statut)
    if current_user.role == RoleUtilisateur.CLUB_MANAGER:
        if not current_user.club_id:
            return []
        query = query.join(Joueur, Joueur.id == JoueurModificationProposee.joueur_id).where(
            Joueur.club_actuel_id == current_user.club_id
        )
    result = await db.execute(query.order_by(JoueurModificationProposee.id.desc()).limit(100))
    return result.scalars().all()



@router.get("/photos/en-attente", response_model=list[PhotoEnAttenteOut])
async def photos_en_attente(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    """File de validation de l'organisateur : photos proposées, jamais publiques."""
    result = await db.execute(
        select(Photo)
        .where(Photo.statut == StatutPhoto.EN_ATTENTE)
        .options(selectinload(Photo.uploadeur))
        .order_by(Photo.id.desc())
        .limit(100)
    )
    photos = result.scalars().all()
    sortie = []
    for ph in photos:
        ligne = PhotoEnAttenteOut.model_validate(ph)
        ligne.url = url_publique(ph.storage_key)
        if ph.sujet_type == "joueur":
            j = await db.get(Joueur, ph.sujet_id)
            if j:
                ligne.sujet_nom = j.nom_complet
                ligne.sujet_club_id = j.club_actuel_id
                ligne.sujet_poste = getattr(j.poste, "value", j.poste)
        else:
            s = await db.get(Staff, ph.sujet_id)
            if s:
                ligne.sujet_nom = s.nom_complet
                ligne.sujet_club_id = s.club_id
                ligne.sujet_poste = getattr(s.role, "value", s.role)
        ligne.propose_par = ph.uploadeur.nom_complet if ph.uploadeur else None
        sortie.append(ligne)
    return sortie


@router.post("/{joueur_id}/photo", response_model=PhotoOut, status_code=status.HTTP_201_CREATED)
async def proposer_photo_joueur(
    joueur_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.CLUB_MANAGER, RoleUtilisateur.COACH, RoleUtilisateur.ADMIN)
    ),
):
    """Le club propose une photo : elle entre EN_ATTENTE, rien ne change côté public."""
    joueur = await db.get(Joueur, joueur_id)
    if joueur is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Joueur introuvable.")
    if current_user.role in (RoleUtilisateur.CLUB_MANAGER, RoleUtilisateur.COACH):
        verifier_scope_club(current_user, joueur.club_actuel_id or -1)
    data = await file.read()
    rang = await db.execute(
        select(func.coalesce(func.max(Photo.version), 0)).where(
            Photo.sujet_type == "joueur", Photo.sujet_id == joueur_id
        )
    )
    version = int(rang.scalar() or 0) + 1
    try:
        key, taille = await uploader_photo("joueur", joueur_id, version, file.content_type or "", data)
    except DepotRefus as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    photo = Photo(
        sujet_type="joueur",
        sujet_id=joueur_id,
        storage_key=key,
        mime_type=file.content_type,
        file_size=taille,
        uploaded_by=current_user.id,
        version=version,
    )
    db.add(photo)
    await db.flush()
    await log_audit(db, "photos", photo.id, ActionAudit.INSERT, current_user.id, None,
                    {"sujet": f"joueur:{joueur_id}", "version": version})
    await db.commit()
    await db.refresh(photo)
    sortie = PhotoOut.model_validate(photo)
    sortie.url = url_publique(photo.storage_key)
    return sortie


@router.post("/photos/{photo_id}/valider", response_model=PhotoOut)
async def valider_photo(
    photo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    """L'organisateur valide : la photo devient officielle, l'ancienne passe en historique."""
    from datetime import datetime, timezone

    photo = await db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo introuvable.")
    if photo.statut != StatutPhoto.EN_ATTENTE:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cette photo a déjà été traitée.")
    photo.statut = StatutPhoto.VALIDEE
    photo.reviewed_by = current_user.id
    photo.reviewed_at = datetime.now(timezone.utc)
    if photo.sujet_type == "joueur":
        sujet = await db.get(Joueur, photo.sujet_id)
    else:
        sujet = await db.get(Staff, photo.sujet_id)
    if sujet is not None:
        sujet.photo_actuelle_id = photo.id
    await log_audit(db, "photos", photo.id, ActionAudit.VALIDATE, current_user.id,
                    {"statut": "en_attente"}, {"statut": "validee"})
    await db.commit()
    await db.refresh(photo)
    sortie = PhotoOut.model_validate(photo)
    sortie.url = url_publique(photo.storage_key)
    return sortie


@router.post("/photos/{photo_id}/rejeter", response_model=PhotoOut)
async def rejeter_photo(
    photo_id: int,
    payload: PhotoRejet,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    """Rejet motivé : la photo officielle précédente reste seule publique."""
    from datetime import datetime, timezone

    photo = await db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo introuvable.")
    if photo.statut != StatutPhoto.EN_ATTENTE:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cette photo a déjà été traitée.")
    photo.statut = StatutPhoto.REJETEE
    photo.motif_refus = payload.motif
    photo.reviewed_by = current_user.id
    photo.reviewed_at = datetime.now(timezone.utc)
    await log_audit(db, "photos", photo.id, ActionAudit.REJECT, current_user.id,
                    {"statut": "en_attente"}, {"statut": "rejetee", "motif": payload.motif.value})
    await db.commit()
    await db.refresh(photo)
    sortie = PhotoOut.model_validate(photo)
    sortie.url = url_publique(photo.storage_key)
    return sortie


@router.put("/{joueur_id}/statut", response_model=JoueurDetailOut)
async def changer_statut_joueur(
    joueur_id: int,
    payload: JoueurStatutUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    """Archiver, suspendre, libérer : jamais de suppression silencieuse."""
    joueur = await db.get(Joueur, joueur_id)
    if joueur is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Joueur introuvable.")
    avant = getattr(joueur.statut, "value", joueur.statut)
    joueur.statut = payload.statut
    await log_audit(db, "joueurs", joueur.id, ActionAudit.UPDATE, current_user.id,
                    {"statut": avant}, {"statut": getattr(payload.statut, "value", payload.statut)})
    await db.commit()
    await db.refresh(joueur)
    return joueur


@router.get("/{joueur_id}", response_model=JoueurPublicOut)
async def profil_public_joueur(joueur_id: int, db: AsyncSession = Depends(get_db)):
    """
    Profil PUBLIC. N'expose jamais téléphone/email (§9.3), et applique
    les restrictions mineurs (§7.4, §10.3) : le schéma JoueurPublicOut
    n'inclut de toute façon pas ces champs, donc aucune fuite possible
    même pour un mineur.
    """
    result = await db.execute(
        select(Joueur).where(Joueur.id == joueur_id).options(selectinload(Joueur.photo_actuelle_rel))
    )
    joueur = result.scalars().first()
    if joueur is None or joueur.anonymise:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Joueur introuvable.")
    return joueur


@router.get("/{joueur_id}/detail", response_model=JoueurDetailOut)
async def detail_prive_joueur(
    joueur_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR, RoleUtilisateur.CLUB_MANAGER)
    ),
):
    """Vue réservée au staff : inclut téléphone/email (§9.3 : endpoints protégés)."""
    result = await db.execute(
        select(Joueur).where(Joueur.id == joueur_id).options(selectinload(Joueur.photo_actuelle_rel))
    )
    joueur = result.scalars().first()
    if joueur is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Joueur introuvable.")
    if current_user.role == RoleUtilisateur.CLUB_MANAGER:
        verifier_scope_club(current_user, joueur.club_actuel_id or -1)
    return joueur


@router.put("/{joueur_id}", response_model=JoueurDetailOut)
async def modifier_joueur_direct(
    joueur_id: int,
    payload: JoueurUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR, RoleUtilisateur.CLUB_MANAGER)
    ),
):
    joueur = await db.get(Joueur, joueur_id)
    if joueur is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Joueur introuvable.")
    if current_user.role == RoleUtilisateur.CLUB_MANAGER:
        verifier_scope_club(current_user, joueur.club_actuel_id or -1)
    data = payload.model_dump(exclude_unset=True)
    avant = {k: getattr(joueur, k) for k in data}
    for k, v in data.items():
        setattr(joueur, k, v)
    await log_audit(db, "joueurs", joueur.id, ActionAudit.UPDATE, current_user.id, avant, data)
    await db.commit()
    await db.refresh(joueur)
    return joueur


@router.post("", response_model=JoueurDetailOut, status_code=status.HTTP_201_CREATED)
async def creer_joueur(
    payload: JoueurCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            RoleUtilisateur.ADMIN,
            RoleUtilisateur.ORGANISATEUR,
            RoleUtilisateur.CLUB_MANAGER,
            RoleUtilisateur.COLLECTEUR,
        )
    ),
):
    if current_user.role == RoleUtilisateur.CLUB_MANAGER:
        if not current_user.club_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Aucun club rattaché à ce compte.")
        payload = payload.model_copy(update={"club_actuel_id": current_user.club_id})
        verifier_scope_club(current_user, payload.club_actuel_id)

    # §7.4 : mineur -> autorisation parentale requise avant toute création publique.
    from datetime import date
    age = date.today().year - payload.date_naissance.year
    if age < 18 and payload.autorisation_parentale is not True:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Un joueur mineur ne peut être créé sans autorisation_parentale=true.",
        )

    doublons = await rechercher_doublons(db, payload.nom_complet, payload.date_naissance, payload.poste)
    statut_verif = (
        StatutVerificationJoueur.DOUBLON_SUSPECTE if doublons else StatutVerificationJoueur.VERIFIE
    )

    joueur = Joueur(**payload.model_dump(), statut_verification=statut_verif)
    db.add(joueur)
    await db.flush()
    await log_audit(db, "joueurs", joueur.id, ActionAudit.INSERT, current_user.id, None, {"nom_complet": joueur.nom_complet})
    await db.commit()
    await db.refresh(joueur)
    return joueur


@router.post("/detect-doublon", response_model=list[JoueurDetailOut])
async def detecter_doublon(payload: JoueurCreate, db: AsyncSession = Depends(get_db)):
    return await rechercher_doublons(db, payload.nom_complet, payload.date_naissance, payload.poste)


@router.post("/merge", response_model=JoueurDetailOut)
async def fusionner(
    payload: JoueurMergeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN)),
):
    try:
        maitre = await fusionner_joueurs(db, payload.joueur_maitre_id, payload.joueur_esclave_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    await log_audit(
        db, "joueurs", payload.joueur_esclave_id, ActionAudit.MERGE, current_user.id,
        None, {"fusionne_vers_id": payload.joueur_maitre_id},
    )
    await db.commit()
    await db.refresh(maitre)
    return maitre


@router.post("/{joueur_id}/proposer-modification", response_model=ModificationProposeeOut, status_code=status.HTTP_201_CREATED)
async def proposer_modification(
    joueur_id: int,
    payload: ModificationProposeeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.CLUB_MANAGER, RoleUtilisateur.ADMIN)),
):
    """
    Workflow validé en Phase 0 (décision C1) : les champs sensibles
    (club, date de naissance, nom, poste) ne sont jamais modifiés
    directement par un club_manager - ils passent par une proposition
    approuvée par l'admin/organisateur. Les champs non sensibles
    (téléphone, email) peuvent être modifiés directement via PUT.
    """
    joueur = await db.get(Joueur, joueur_id)
    if joueur is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Joueur introuvable.")
    if current_user.role == RoleUtilisateur.CLUB_MANAGER:
        verifier_scope_club(current_user, joueur.club_actuel_id or -1)
    if payload.champ not in CHAMPS_SENSIBLES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"'{payload.champ}' n'est pas un champ soumis à proposition. "
            f"Champs concernés : {sorted(CHAMPS_SENSIBLES)}. "
            f"Les champs {sorted(CHAMPS_MODIFIABLES_DIRECTEMENT)} se modifient directement.",
        )
    proposition = JoueurModificationProposee(
        joueur_id=joueur_id,
        proposee_par_id=current_user.id,
        champ=payload.champ,
        ancienne_valeur=str(getattr(joueur, payload.champ, None)),
        nouvelle_valeur=payload.nouvelle_valeur,
    )
    db.add(proposition)
    await db.commit()
    await db.refresh(proposition)
    return proposition


@router.put("/propositions/{proposition_id}/approuver", response_model=ModificationProposeeOut)
async def approuver_proposition(
    proposition_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    from datetime import datetime, timezone

    proposition = await db.get(JoueurModificationProposee, proposition_id)
    if proposition is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proposition introuvable.")
    if proposition.statut != "en_attente":
        raise HTTPException(status.HTTP_409_CONFLICT, "Cette proposition a déjà été traitée.")

    joueur = await db.get(Joueur, proposition.joueur_id)
    setattr(joueur, proposition.champ, proposition.nouvelle_valeur)
    proposition.statut = "approuvee"
    proposition.traitee_par_id = current_user.id
    proposition.date_traitement = datetime.now(timezone.utc)

    await log_audit(
        db, "joueurs", joueur.id, ActionAudit.UPDATE, current_user.id,
        {proposition.champ: proposition.ancienne_valeur},
        {proposition.champ: proposition.nouvelle_valeur},
    )
    await db.commit()
    await db.refresh(proposition)
    return proposition
