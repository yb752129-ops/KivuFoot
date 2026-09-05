from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.rbac import require_roles, verifier_scope_club
from app.database import get_db
from app.models.enums import ActionAudit, RoleUtilisateur, StatutVerificationJoueur
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
from app.services.detection_doublons import fusionner_joueurs, rechercher_doublons

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


@router.get("/{joueur_id}", response_model=JoueurPublicOut)
async def profil_public_joueur(joueur_id: int, db: AsyncSession = Depends(get_db)):
    """
    Profil PUBLIC. N'expose jamais téléphone/email (§9.3), et applique
    les restrictions mineurs (§7.4, §10.3) : le schéma JoueurPublicOut
    n'inclut de toute façon pas ces champs, donc aucune fuite possible
    même pour un mineur.
    """
    joueur = await db.get(Joueur, joueur_id)
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
    joueur = await db.get(Joueur, joueur_id)
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
