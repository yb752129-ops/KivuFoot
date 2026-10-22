import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete as sql_delete, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import CLUB_ROLES, isClubRole, require_roles, verifier_organisateur_de_competition, verifier_organisateur_du_match
from app.config import settings
from app.database import get_db
from app.models.competition import Saison
from app.models.enums import (
    ActionAudit,
    EquipeConcernee,
    PeriodeMatch,
    RoleUtilisateur,
    StatutMatch,
    StatutValidationEvenement,
    TypeEvenement,
)
from app.models.evenement import EvenementMatch
from app.models.joueur import Joueur
from app.models.match import Match, MatchParticipation
from app.models.user import User
from app.schemas.evenement import EvenementOut
from app.schemas.match import (
    AnnulationResultatRetroactif,
    ButeursVerifiesCreate,
    MatchAnnulationCreate,
    MatchCreate,
    MatchOut,
    MatchPhaseUpdate,
    MatchProgrammationUpdate,
    MatchResultatRetroactif,
    ParticipationCreate,
    ParticipationOut,
    ParticipationUpdate,
)
from app.services.audit import log_audit
from app.services.groupes_saison import determiner_groupe_match
from app.schemas.match import (
    CompositionEquipeIn,
    CompositionEquipeOut,
    CompositionJoueurOut,
    CompositionOut,
    CompositionStaffOut,
)
from app.schemas.sport_engine import ChecklistOut, EligibiliteOut
from app.services.checklist_validation import bloquants_effectifs, run_checklist, save_checklist
from app.services.eligibilite import verifier_joueur
from app.services.documents_officiels import generer_document_match
from app.models.club import Club
from app.models.competition import Competition
from app.models.staff import Staff
from app.services.calcul_stats import appliquer_evenement_valide
from app.services.recalcul_stats import reconstruire_stats_saison
from app.services.reglements import get_reglement_actif, get_reglement_pour_match
from app.services.validation import valider_match
from app.services.possession import suspendre_possession, terminer_possession
from app.services.composition_positions import positions_titulaires_valides, slots_formation
from app.services.statut_equipe import match_a_une_equipe_retiree, match_sans_equipe_retiree

router = APIRouter(prefix="/matchs", tags=["Matchs"])


def _value(value):
    return value.value if hasattr(value, "value") else value


@router.get("", response_model=list[MatchOut])
async def lister_matchs(
    db: AsyncSession = Depends(get_db),
    saison_id: int | None = None,
    phase: str | None = None,
    groupe: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """
    Public Accueil : programme (à venir), en_cours, termine (sifflé),
    valide. Pas `conteste`. Le classement reste calculé sur `valide`.
    """
    query = select(Match).where(
        Match.statut.in_([
            StatutMatch.PROGRAMME.value,
            StatutMatch.EN_COURS.value,
            StatutMatch.TERMINE.value,
            StatutMatch.VALIDE.value,
        ])
    )
    if saison_id:
        query = query.where(Match.saison_id == saison_id)
    # Le retrait masque le match de toutes les projections publiques, sans
    # toucher à son statut ni à ses événements en base.
    query = query.where(match_sans_equipe_retiree())
    if phase:
        query = query.where(Match.phase == phase)
    if groupe:
        query = query.where(Match.groupe == groupe)
    result = await db.execute(query.order_by(Match.date_heure.desc()).limit(min(limit, 100)).offset(offset))
    return result.scalars().all()


@router.get("/gestion", response_model=list[MatchOut])
async def lister_matchs_gestion(
    db: AsyncSession = Depends(get_db),
    saison_id: int | None = None,
    phase: str | None = None,
    groupe: str | None = None,
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
    limit: int = 50,
    offset: int = 0,
):
    """Tous les statuts — réservé organisateur / admin (Phase 5)."""
    query = select(Match)
    if saison_id:
        query = query.where(Match.saison_id == saison_id)
    if phase:
        query = query.where(Match.phase == phase)
    if groupe:
        query = query.where(Match.groupe == groupe)
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
    statut = (
        match_.statut.value if hasattr(match_.statut, "value") else match_.statut
    ) if match_ else None
    if match_ is None or statut not in ("programme", "en_cours", "termine", "valide"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable ou non publié.")
    if await match_a_une_equipe_retiree(db, match_):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable ou non publié.")
    return match_


@router.get("/{match_id}/checklist-validation", response_model=ChecklistOut)
async def checklist_validation(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    match_ = await verifier_organisateur_du_match(match_id, current_user, db)
    return await run_checklist(db, match_)


@router.get("/{match_id}/eligibilite", response_model=list[EligibiliteOut])
async def eligibilite_match(
    match_id: int,
    club_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            RoleUtilisateur.ADMIN,
            RoleUtilisateur.ORGANISATEUR,
            *CLUB_ROLES,
        )
    ),
):
    match_ = await db.get(Match, match_id)
    if match_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    if _value(match_.statut) == StatutMatch.ANNULE.value:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    if club_id not in (match_.equipe_domicile_id, match_.equipe_exterieur_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cette équipe ne participe pas à ce match.")
    role = _value(current_user.role)
    if role in (RoleUtilisateur.ADMIN.value, RoleUtilisateur.ORGANISATEUR.value):
        await verifier_organisateur_du_match(match_id, current_user, db)
    elif current_user.club_id != club_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Vous ne gérez pas cette équipe.")
    joueurs = (
        await db.execute(select(Joueur.id).where(Joueur.club_actuel_id == club_id))
    ).scalars().all()
    return [await verifier_joueur(db, match_, joueur_id, club_id) for joueur_id in joueurs]


@router.get("/{match_id}/eligibilite/{joueur_id}", response_model=EligibiliteOut)
async def eligibilite_joueur(
    match_id: int,
    joueur_id: int,
    club_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            RoleUtilisateur.ADMIN,
            RoleUtilisateur.ORGANISATEUR,
            *CLUB_ROLES,
        )
    ),
):
    match_ = await db.get(Match, match_id)
    if match_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    if _value(match_.statut) == StatutMatch.ANNULE.value:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    if club_id not in (match_.equipe_domicile_id, match_.equipe_exterieur_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cette équipe ne participe pas à ce match.")
    role = _value(current_user.role)
    if role in (RoleUtilisateur.ADMIN.value, RoleUtilisateur.ORGANISATEUR.value):
        await verifier_organisateur_du_match(match_id, current_user, db)
    elif current_user.club_id != club_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Vous ne gérez pas cette équipe.")
    return await verifier_joueur(db, match_, joueur_id, club_id)


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

    groupe_officiel = await determiner_groupe_match(
        db,
        payload.saison_id,
        payload.equipe_domicile_id,
        payload.equipe_exterieur_id,
        payload.phase,
        payload.groupe,
    )
    donnees = payload.model_dump()
    donnees["groupe"] = groupe_officiel
    reglement = await get_reglement_actif(db, payload.saison_id)
    if reglement is not None:
        donnees["reglement_version_id"] = reglement.id
    match_ = Match(**donnees)
    db.add(match_)
    await db.flush()
    await log_audit(db, "matchs", match_.id, ActionAudit.INSERT, current_user.id, None, {"saison_id": payload.saison_id})
    await db.commit()
    await db.refresh(match_)
    return match_


@router.delete("/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
async def supprimer_match_programme(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    """Supprime uniquement un match encore programmé et non verrouillé.

    Cette porte est volontairement étroite : elle sert à corriger une double
    programmation avant le coup d'envoi. Un match commencé, terminé, validé,
    verrouillé ou déjà enrichi de faits/participations ne peut pas être effacé.
    """
    match_ = await verifier_organisateur_du_match(match_id, current_user, db)
    statut = match_.statut.value if hasattr(match_.statut, "value") else match_.statut
    if match_.locked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ce match est verrouillé.")
    if statut != StatutMatch.PROGRAMME.value and statut != StatutMatch.PROGRAMME:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Seul un match encore programmé peut être supprimé.",
        )
    date_heure = match_.date_heure
    if date_heure.tzinfo is None:
        date_heure = date_heure.replace(tzinfo=timezone.utc)
    if match_.started_at is not None or date_heure <= datetime.now(timezone.utc):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ce match a déjà commencé ou son coup d’envoi est dépassé.",
        )
    evenement = await db.execute(
        select(EvenementMatch.id).where(EvenementMatch.match_id == match_id).limit(1)
    )
    participation = await db.execute(
        select(MatchParticipation.id).where(MatchParticipation.match_id == match_id).limit(1)
    )
    if evenement.scalar_one_or_none() is not None or participation.scalar_one_or_none() is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ce match contient déjà des données sportives et ne peut pas être supprimé.",
        )
    avant = {
        "saison_id": match_.saison_id,
        "journee": match_.journee,
        "date_heure": match_.date_heure.isoformat(),
        "equipe_domicile_id": match_.equipe_domicile_id,
        "equipe_exterieur_id": match_.equipe_exterieur_id,
        "stade": match_.stade,
        "statut": statut,
    }
    await log_audit(db, "matchs", match_.id, ActionAudit.DELETE, current_user.id, avant, None)
    await db.execute(sql_delete(Match).where(Match.id == match_id))
    await db.commit()
    return None


@router.put("/{match_id}/statut", response_model=MatchOut)
async def changer_statut_match(
    match_id: int,
    nouveau_statut: StatutMatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR, RoleUtilisateur.COLLECTEUR)
    ),
):
    """
    Cycle de vie (Phase 1) : programme -> en_cours -> termine -> valide,
    ou conteste à tout moment. La transition vers 'valide' passe
    obligatoirement par la route dédiée /matchs/{id}/valider (elle seule
    vérifie qu'aucun événement n'est en attente et verrouille le match).
    Collecteur : démarre et termine seulement (CDC Accueil).
    """
    if current_user.role == RoleUtilisateur.COLLECTEUR:
        match_ = await db.get(Match, match_id)
        if match_ is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
        if nouveau_statut not in (StatutMatch.EN_COURS, StatutMatch.TERMINE):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Le collecteur démarre ou termine. Valider et contester restent à l'organisateur.",
            )
    else:
        match_ = await verifier_organisateur_du_match(match_id, current_user, db)
    if nouveau_statut == StatutMatch.ANNULE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Utilisez POST /matchs/{id}/annuler avec un motif : l'annulation est auditée et réversible.",
        )
    if _value(match_.statut) == StatutMatch.ANNULE.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce match est annulé : utilisez POST /matchs/{id}/retablir.")
    if match_.locked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ce match est verrouillé.")
    if nouveau_statut == StatutMatch.VALIDE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Utilisez POST /matchs/{id}/valider pour valider un match (vérifications supplémentaires requises).",
        )
    actuel = match_.statut.value if hasattr(match_.statut, "value") else match_.statut
    now = datetime.now(timezone.utc)
    if nouveau_statut == StatutMatch.EN_COURS:
        if actuel != StatutMatch.PROGRAMME.value and actuel != StatutMatch.PROGRAMME:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Seul un match programmé peut être démarré.")
        match_.started_at = now
        match_.ended_at = None
        match_.periode = PeriodeMatch.PREMIERE
        match_.periode_started_at = now
        match_.paused_at = None
    elif nouveau_statut == StatutMatch.TERMINE:
        if actuel != StatutMatch.EN_COURS.value and actuel != StatutMatch.EN_COURS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Seul un match en cours peut être terminé.")
        match_.ended_at = now
    old_statut = actuel
    match_.statut = nouveau_statut
    # Couche additive : la fin du match ferme uniquement l'intervalle de
    # possession éventuel. Elle ne lit ni ne modifie aucun événement sportif.
    if nouveau_statut == StatutMatch.TERMINE:
        await terminer_possession(db, match_.id, current_user.id, now=now)
    await log_audit(db, "matchs", match_.id, ActionAudit.UPDATE, current_user.id, {"statut": old_statut}, {"statut": nouveau_statut.value})
    await db.commit()
    await db.refresh(match_)
    return match_


@router.post("/{match_id}/annuler", response_model=MatchOut)
async def annuler_match(
    match_id: int,
    payload: MatchAnnulationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)
    ),
):
    """Annule un match sans supprimer sa ligne, ses faits ni sa feuille.

    La route est la seule porte d'annulation : elle mémorise le statut et le
    verrou précédents, marque le match annulé et reconstruit les statistiques
    joueur depuis les matchs encore valides. Le recalcul est atomique avec
    l'audit et l'action peut être inversée par ``/retablir``.
    """
    if current_user.role == RoleUtilisateur.ORGANISATEUR:
        await verifier_organisateur_du_match(match_id, current_user, db)
    match_ = await db.scalar(select(Match).where(Match.id == match_id).with_for_update())
    if match_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    actuel = _value(match_.statut)
    if actuel == StatutMatch.ANNULE.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce match est déjà annulé.")

    now = datetime.now(timezone.utc)
    avant = {
        "statut": actuel,
        "locked": bool(match_.locked),
        "motif_annulation": match_.annule_motif,
    }
    match_.statut_avant_annulation = actuel
    match_.locked_avant_annulation = bool(match_.locked)
    match_.annule_motif = payload.motif
    match_.annule_par_id = current_user.id
    match_.annule_at = now
    match_.statut = StatutMatch.ANNULE
    # Les événements sont conservés et doivent rester immuables pendant que
    # le match est masqué. Le verrou d'origine est restauré par /retablir.
    match_.locked = True
    await db.flush()

    await reconstruire_stats_saison(db, match_.saison_id)
    await log_audit(
        db,
        "matchs",
        match_.id,
        ActionAudit.UPDATE,
        current_user.id,
        avant,
        {
            "statut": StatutMatch.ANNULE.value,
            "locked": True,
            "statut_avant_annulation": actuel,
            "motif_annulation": payload.motif,
            "annule_par_id": current_user.id,
            "annule_at": now.isoformat(),
        },
    )
    await db.commit()
    await db.refresh(match_)
    return match_


@router.post("/{match_id}/retablir", response_model=MatchOut)
async def retablir_match(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)
    ),
):
    """Restaure exactement le statut/verrou qui précédaient l'annulation."""
    if current_user.role == RoleUtilisateur.ORGANISATEUR:
        await verifier_organisateur_du_match(match_id, current_user, db)
    match_ = await db.scalar(select(Match).where(Match.id == match_id).with_for_update())
    if match_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    if _value(match_.statut) != StatutMatch.ANNULE.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce match n'est pas annulé.")
    if not match_.statut_avant_annulation:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "L'état précédent de ce match est introuvable : restauration refusée pour éviter une supposition.",
        )
    try:
        statut_restaure = StatutMatch(match_.statut_avant_annulation)
    except ValueError:
        raise HTTPException(status.HTTP_409_CONFLICT, "L'ancien statut du match est invalide.")
    if statut_restaure == StatutMatch.ANNULE:
        raise HTTPException(status.HTTP_409_CONFLICT, "Un match annulé ne peut pas être restauré vers annule.")

    motif = match_.annule_motif
    avant = {
        "statut": StatutMatch.ANNULE.value,
        "locked": bool(match_.locked),
        "motif_annulation": motif,
        "statut_avant_annulation": match_.statut_avant_annulation,
    }
    locked_restaure = bool(match_.locked_avant_annulation)
    match_.statut = statut_restaure
    match_.locked = locked_restaure
    match_.statut_avant_annulation = None
    match_.locked_avant_annulation = None
    match_.annule_motif = None
    match_.annule_par_id = None
    match_.annule_at = None
    await db.flush()

    await reconstruire_stats_saison(db, match_.saison_id)
    await log_audit(
        db,
        "matchs",
        match_.id,
        ActionAudit.UPDATE,
        current_user.id,
        avant,
        {
            "statut": statut_restaure.value,
            "locked": locked_restaure,
            "motif_annulation": motif,
            "retabli_par_id": current_user.id,
        },
    )
    await db.commit()
    await db.refresh(match_)
    return match_


@router.put("/{match_id}/programmation", response_model=MatchOut)
async def modifier_programmation_match(
    match_id: int,
    payload: MatchProgrammationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    """Modifie la date, l'heure et éventuellement le stade d'un match à venir."""
    match_ = await verifier_organisateur_du_match(match_id, current_user, db)
    if match_.locked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ce match est verrouillé.")
    statut = match_.statut.value if hasattr(match_.statut, "value") else match_.statut
    if statut != StatutMatch.PROGRAMME.value and statut != StatutMatch.PROGRAMME:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Seul un match programmé peut être replanifié.")
    avant = {"date_heure": match_.date_heure.isoformat(), "stade": match_.stade}
    match_.date_heure = payload.date_heure
    if payload.stade is not None:
        match_.stade = payload.stade.strip() or None
    apres = {"date_heure": match_.date_heure.isoformat(), "stade": match_.stade}
    await log_audit(db, "matchs", match_.id, ActionAudit.UPDATE, current_user.id, avant, apres)
    await db.commit()
    await db.refresh(match_)
    return match_


@router.put("/{match_id}/periode", response_model=MatchOut)
async def changer_periode_match(
    match_id: int,
    periode: PeriodeMatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR, RoleUtilisateur.COLLECTEUR)
    ),
):
    """Mi-temps / reprise : le match reste EN COURS (C5). Ce n'est pas un statut."""
    if current_user.role == RoleUtilisateur.COLLECTEUR:
        match_ = await db.get(Match, match_id)
        if match_ is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    else:
        match_ = await verifier_organisateur_du_match(match_id, current_user, db)
    if match_.locked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ce match est verrouillé.")
    actuel_statut = match_.statut.value if hasattr(match_.statut, "value") else match_.statut
    if actuel_statut != StatutMatch.EN_COURS.value:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Seul un match en cours a une période à changer.")
    actuelle = match_.periode.value if match_.periode and hasattr(match_.periode, "value") else match_.periode
    now = datetime.now(timezone.utc)
    if periode == PeriodeMatch.MI_TEMPS:
        if actuelle not in (PeriodeMatch.PREMIERE.value, PeriodeMatch.PREMIERE, None, "1"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "La mi-temps se siffle à la fin de la première période.")
        match_.paused_at = now
        match_.periode = PeriodeMatch.MI_TEMPS
    elif periode == PeriodeMatch.SECONDE:
        if actuelle not in (PeriodeMatch.MI_TEMPS.value, PeriodeMatch.MI_TEMPS, "mi_temps"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "La deuxième période commence après la mi-temps.")
        match_.periode = PeriodeMatch.SECONDE
        match_.periode_started_at = now
    elif periode == PeriodeMatch.PREMIERE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La première période démarre avec le coup d'envoi.")
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Période inconnue.")
    # La mi-temps suspend automatiquement la capture. La reprise ne
    # redémarre jamais A/B toute seule : le collecteur doit choisir.
    if periode == PeriodeMatch.MI_TEMPS:
        await suspendre_possession(db, match_.id, current_user.id, now=now)
    await log_audit(
        db,
        "matchs",
        match_.id,
        ActionAudit.UPDATE,
        current_user.id,
        {"periode": actuelle},
        {"periode": periode.value},
    )
    await db.commit()
    await db.refresh(match_)
    return match_


@router.post("/{match_id}/valider", response_model=MatchOut)
async def valider_match_route(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    match_ = await verifier_organisateur_du_match(match_id, current_user, db)
    # Lock before the checklist so a concurrent composition cannot be
    # accepted between the checklist read and the final validation.
    match_ = await db.scalar(select(Match).where(Match.id == match_id).with_for_update())
    checklist = await run_checklist(db, match_)
    bloquants = bloquants_effectifs(checklist)
    if bloquants:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "message": "Impossible de valider ce match : la checklist contient des contrôles bloquants.",
                "checklist": checklist.model_dump(mode="json"),
                "bloquants": [control.model_dump(mode="json") for control in bloquants],
            },
        )
    await save_checklist(db, match_, checklist, current_user.id)
    match_ = await valider_match(db, match_id, current_user.id)
    await db.commit()
    # Le PDF est un dérivé : une panne de génération ne doit jamais annuler
    # la validation sportive déjà commitée. Une relance reste possible via
    # /documents/matchs/{id}/generer.
    try:
        await generer_document_match(db, match_id, current_user.id)
        await db.commit()
    except Exception:
        await db.rollback()
    await db.refresh(match_)
    return match_



@router.post("/{match_id}/resultat-retroactif", response_model=MatchOut)
async def enregistrer_resultat_retroactif(
    match_id: int,
    payload: MatchResultatRetroactif,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    """Publie un résultat officiel saisi après coup, sans inventer le live."""
    match_ = await verifier_organisateur_du_match(match_id, current_user, db)
    if match_.locked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ce match est déjà verrouillé.")

    statut = match_.statut.value if hasattr(match_.statut, "value") else match_.statut
    if statut != StatutMatch.PROGRAMME.value and statut != StatutMatch.PROGRAMME:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Le résultat rétrospectif s'applique uniquement à un match encore programmé.",
        )

    deja = await db.execute(select(EvenementMatch.id).where(EvenementMatch.match_id == match_id).limit(1))
    if deja.first() is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ce match possède déjà des événements : utilisez le flux normal de validation.",
        )

    ancien = {
        "statut": statut,
        "score_domicile": match_.score_domicile,
        "score_exterieur": match_.score_exterieur,
        "resultat_retroactif": match_.resultat_retroactif,
    }
    match_.score_domicile = payload.score_domicile
    match_.score_exterieur = payload.score_exterieur
    match_.statut = StatutMatch.TERMINE
    match_.resultat_retroactif = True
    match_.motif_resultat_retroactif = payload.motif
    match_.note_officielle = payload.note_officielle
    match_.buteurs_a_verifier = payload.score_domicile + payload.score_exterieur > 0
    await db.flush()

    await log_audit(
        db,
        "matchs",
        match_.id,
        ActionAudit.UPDATE,
        current_user.id,
        ancien,
        {
            "statut": "termine",
            "score_domicile": match_.score_domicile,
            "score_exterieur": match_.score_exterieur,
            "resultat_retroactif": True,
            "buteurs_a_verifier": match_.buteurs_a_verifier,
            "motif": payload.motif,
        },
    )

    match_ = await valider_match(db, match_id, current_user.id)
    await db.commit()
    await db.refresh(match_)
    return match_


@router.post("/{match_id}/annuler-resultat-retroactif", response_model=MatchOut)
async def annuler_resultat_retroactif(
    match_id: int,
    payload: AnnulationResultatRetroactif,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    """Révoque une correction rétroactive erronée, avec audit obligatoire.

    Le match revient à l'état programmé et peut ensuite être reprogrammé
    via la route normale. La révocation est refusée si des événements ou
    des participations existent : aucune suppression silencieuse.
    """
    match_ = await verifier_organisateur_du_match(match_id, current_user, db)
    if not match_.locked or not match_.resultat_retroactif:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ce match n'est pas un résultat rétroactif verrouillé à révoquer.",
        )

    evenement = await db.execute(
        select(EvenementMatch.id).where(EvenementMatch.match_id == match_id).limit(1)
    )
    if evenement.first() is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Révocation bloquée : ce match possède déjà des événements validés.",
        )
    participation = await db.execute(
        select(MatchParticipation.id).where(MatchParticipation.match_id == match_id).limit(1)
    )
    if participation.first() is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Révocation bloquée : ce match possède déjà une feuille de match.",
        )

    ancien = {
        "statut": getattr(match_.statut, "value", match_.statut),
        "score_domicile": match_.score_domicile,
        "score_exterieur": match_.score_exterieur,
        "locked": match_.locked,
        "resultat_retroactif": match_.resultat_retroactif,
        "motif_resultat_retroactif": match_.motif_resultat_retroactif,
        "note_officielle": match_.note_officielle,
        "buteurs_a_verifier": match_.buteurs_a_verifier,
    }
    match_.score_domicile = 0
    match_.score_exterieur = 0
    match_.statut = StatutMatch.PROGRAMME
    match_.started_at = None
    match_.ended_at = None
    match_.periode = None
    match_.periode_started_at = None
    match_.paused_at = None
    match_.forfait = False
    match_.forfait_equipe = None
    match_.valide_par = None
    match_.date_validation = None
    match_.locked = False
    match_.resultat_retroactif = False
    match_.motif_resultat_retroactif = None
    match_.note_officielle = None
    match_.buteurs_a_verifier = False
    await log_audit(
        db,
        "matchs",
        match_.id,
        ActionAudit.UPDATE,
        current_user.id,
        ancien,
        {
            "statut": StatutMatch.PROGRAMME.value,
            "score_domicile": 0,
            "score_exterieur": 0,
            "locked": False,
            "resultat_retroactif": False,
            "motif_annulation": payload.motif,
        },
    )
    await db.commit()
    await db.refresh(match_)
    return match_


@router.post("/{match_id}/buteurs-verifies", response_model=list[EvenementOut])
async def ajouter_buteurs_verifies(
    match_id: int,
    payload: ButeursVerifiesCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    """Ajoute les buteurs vérifiés d'un résultat rétroactif sans doubler le score."""
    match_ = await verifier_organisateur_du_match(match_id, current_user, db)
    if not match_.locked or not match_.resultat_retroactif:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cette action est réservée à un résultat rétroactif déjà validé.",
        )
    if not match_.buteurs_a_verifier:
        raise HTTPException(status.HTTP_409_CONFLICT, "Les buteurs de ce match sont déjà enregistrés.")

    existants = (
        await db.execute(
            select(EvenementMatch).where(
                EvenementMatch.match_id == match_id,
                EvenementMatch.source == "buteur_verifie",
                EvenementMatch.statut_validation == StatutValidationEvenement.VALIDE,
            )
        )
    ).scalars().all()
    if existants:
        raise HTTPException(status.HTTP_409_CONFLICT, "Des buteurs vérifiés existent déjà pour ce match.")

    total_attendu = match_.score_domicile + match_.score_exterieur
    if len(payload.buteurs) != total_attendu:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Il faut enregistrer exactement {total_attendu} buteur(s) pour le score officiel.",
        )
    nb_dom = sum(b.equipe_concernee == EquipeConcernee.DOMICILE for b in payload.buteurs)
    nb_ext = sum(b.equipe_concernee == EquipeConcernee.EXTERIEUR for b in payload.buteurs)
    if nb_dom != match_.score_domicile or nb_ext != match_.score_exterieur:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "La répartition des buteurs ne correspond pas au score officiel.",
        )

    ajoutes = []
    for buteur in payload.buteurs:
        joueur = await db.get(Joueur, buteur.joueur_id)
        if joueur is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Un joueur indiqué est introuvable.")
        club_id = (
            match_.equipe_exterieur_id
            if buteur.equipe_concernee == EquipeConcernee.EXTERIEUR
            else match_.equipe_domicile_id
        )
        if joueur.club_actuel_id and club_id and joueur.club_actuel_id != club_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Le joueur {joueur.nom_complet} n'appartient pas à l'équipe indiquée.",
            )

        evenement = EvenementMatch(
            match_id=match_id,
            minute=buteur.minute or 0,
            minute_connue=buteur.minute is not None,
            periode=None,
            type=TypeEvenement.BUT,
            joueur_id=buteur.joueur_id,
            equipe_concernee=buteur.equipe_concernee,
            statut_validation=StatutValidationEvenement.VALIDE,
            valide_par=current_user.id,
            date_validation=datetime.now(timezone.utc),
            locked=True,
            score_comptabilise=False,
            source="buteur_verifie",
            temp_id=uuid.uuid4(),
            cree_par_id=current_user.id,
        )
        db.add(evenement)
        await db.flush()
        await appliquer_evenement_valide(db, evenement, match_)
        await log_audit(
            db,
            "evenements_match",
            evenement.id,
            ActionAudit.VALIDATE,
            current_user.id,
            None,
            {"source": "buteur_verifie", "score_comptabilise": False, "joueur_id": buteur.joueur_id},
        )
        ajoutes.append(evenement)

    match_.buteurs_a_verifier = False
    await log_audit(
        db,
        "matchs",
        match_.id,
        ActionAudit.UPDATE,
        current_user.id,
        {"buteurs_a_verifier": True},
        {"buteurs_a_verifier": False},
    )
    await db.commit()
    for evenement in ajoutes:
        await db.refresh(evenement)
    return ajoutes


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
    # Un forfait n'est pas une durée de jeu normale : la capture éventuelle
    # est fermée pour audit mais exclue de toute publication officielle.
    await terminer_possession(
        db,
        match_.id,
        current_user.id,
        now=datetime.now(timezone.utc),
        exclusion_reason="forfait",
    )
    await log_audit(db, "matchs", match_.id, ActionAudit.UPDATE, current_user.id, None, {"forfait": True, "forfait_equipe": equipe_forfait.value})
    await db.commit()
    await db.refresh(match_)
    return match_


@router.post("/{match_id}/participations", response_model=ParticipationOut, status_code=status.HTTP_201_CREATED)
async def ajouter_participation(
    match_id: int,
    payload: ParticipationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR, *CLUB_ROLES)
    ),
):
    """Legacy feuille endpoint kept for the current OrgaMatch frontend.

    It is deliberately subject to the same pre-kickoff, club-scope and
    eligibility rules as the composition endpoint, and every player change
    is auditable. New code should prefer /composition.
    """
    match_ = await db.scalar(select(Match).where(Match.id == match_id).with_for_update())
    if match_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    statut_match = _value(match_.statut)
    if match_.locked or statut_match != StatutMatch.PROGRAMME.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "La feuille n'est modifiable que pour un match programmé et non verrouillé.")
    if payload.club_id not in (match_.equipe_domicile_id, match_.equipe_exterieur_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cette équipe ne participe pas à ce match.")

    role = _value(current_user.role)
    if role in (RoleUtilisateur.ADMIN.value, RoleUtilisateur.ORGANISATEUR.value):
        await verifier_organisateur_du_match(match_id, current_user, db)
    elif not isClubRole(current_user.role) or current_user.club_id != payload.club_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Vous ne gérez pas cette équipe.")

    equipe_attendue = (
        EquipeConcernee.DOMICILE
        if payload.club_id == match_.equipe_domicile_id
        else EquipeConcernee.EXTERIEUR
    )
    if _value(payload.equipe_concernee) != _value(equipe_attendue):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "L'équipe ne correspond pas au club sélectionné.")
    joueur = await db.get(Joueur, payload.joueur_id)
    if joueur is None or joueur.club_actuel_id != payload.club_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Le joueur n'appartient pas à cette équipe.")
    eligibilite = await verifier_joueur(
        db, match_, payload.joueur_id, payload.club_id, equipe=_value(payload.equipe_concernee)
    )
    if eligibilite.statut == "BLOQUANT":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, eligibilite.message)

    duplicate = await db.scalar(
        select(MatchParticipation).where(
            MatchParticipation.match_id == match_id,
            MatchParticipation.joueur_id == payload.joueur_id,
            MatchParticipation.equipe_concernee == _value(payload.equipe_concernee),
        )
    )
    if duplicate is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce joueur figure déjà dans la feuille de match.")
    participation = MatchParticipation(match_id=match_id, **payload.model_dump())
    db.add(participation)
    await db.flush()
    await log_audit(
        db,
        "match_compositions",
        participation.id,
        ActionAudit.INSERT,
        current_user.id,
        None,
        {
            "match_id": match_id,
            "equipe": _value(payload.equipe_concernee),
            "joueur_id": joueur.id,
            "poste": _value(joueur.poste),
            "statut": _value(payload.statut),
            "numero": None,
        },
    )
    await db.commit()
    await db.refresh(participation)
    return participation


@router.put("/{match_id}/participations/{participation_id}", response_model=ParticipationOut)
async def modifier_participation(
    match_id: int,
    participation_id: int,
    payload: ParticipationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR, *CLUB_ROLES)
    ),
):
    match_ = await db.scalar(select(Match).where(Match.id == match_id).with_for_update())
    if match_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    participation = await db.scalar(
        select(MatchParticipation)
        .where(
            MatchParticipation.id == participation_id,
            MatchParticipation.match_id == match_id,
        )
        .with_for_update()
    )
    if participation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Participation introuvable.")
    if match_.locked or _value(match_.statut) != StatutMatch.PROGRAMME.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "La feuille n'est modifiable que pour un match programmé et non verrouillé.")
    if participation.club_id not in (match_.equipe_domicile_id, match_.equipe_exterieur_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "La participation n'est pas rattachée à une équipe de ce match.")
    role = _value(current_user.role)
    if role in (RoleUtilisateur.ADMIN.value, RoleUtilisateur.ORGANISATEUR.value):
        await verifier_organisateur_du_match(match_id, current_user, db)
    elif not isClubRole(current_user.role) or current_user.club_id != participation.club_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Vous ne gérez pas cette équipe.")
    joueur = await db.get(Joueur, participation.joueur_id)
    if joueur is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Le joueur de cette participation est introuvable.")
    eligibilite = await verifier_joueur(
        db, match_, participation.joueur_id, participation.club_id,
        equipe=_value(participation.equipe_concernee),
    )
    if eligibilite.statut == "BLOQUANT":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, eligibilite.message)
    avant = {
        "joueur_id": participation.joueur_id,
        "poste": _value(joueur.poste),
        "statut": _value(participation.statut),
        "numero": participation.numero,
    }
    participation.statut = payload.statut
    apres = {**avant, "statut": _value(payload.statut)}
    await log_audit(db, "match_compositions", participation.id, ActionAudit.UPDATE, current_user.id, avant, apres)
    await db.commit()
    await db.refresh(participation)
    return participation


@router.delete("/{match_id}/participations/{participation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def retirer_participation(
    match_id: int,
    participation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR, *CLUB_ROLES)
    ),
):
    match_ = await db.scalar(select(Match).where(Match.id == match_id).with_for_update())
    if match_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    participation = await db.scalar(
        select(MatchParticipation)
        .where(
            MatchParticipation.id == participation_id,
            MatchParticipation.match_id == match_id,
        )
        .with_for_update()
    )
    if participation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Participation introuvable.")
    if match_.locked or _value(match_.statut) != StatutMatch.PROGRAMME.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "La feuille n'est modifiable que pour un match programmé et non verrouillé.")
    role = _value(current_user.role)
    if role in (RoleUtilisateur.ADMIN.value, RoleUtilisateur.ORGANISATEUR.value):
        await verifier_organisateur_du_match(match_id, current_user, db)
    elif not isClubRole(current_user.role) or current_user.club_id != participation.club_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Vous ne gérez pas cette équipe.")
    joueur = await db.get(Joueur, participation.joueur_id)
    avant = {
        "joueur_id": participation.joueur_id,
        "poste": _value(joueur.poste) if joueur else None,
        "statut": _value(participation.statut),
        "numero": participation.numero,
    }
    await log_audit(db, "match_compositions", participation.id, ActionAudit.DELETE, current_user.id, avant, None)
    await db.delete(participation)
    await db.commit()
    return None


@router.get("/{match_id}/participations", response_model=list[ParticipationOut])
async def lister_participations(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR, *CLUB_ROLES)
    ),
):
    match_ = await db.get(Match, match_id)
    if match_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    role = _value(current_user.role)
    query = select(MatchParticipation).where(MatchParticipation.match_id == match_id)
    if role in (RoleUtilisateur.ADMIN.value, RoleUtilisateur.ORGANISATEUR.value):
        await verifier_organisateur_du_match(match_id, current_user, db)
    else:
        if not isClubRole(current_user.role) or current_user.club_id not in (
            match_.equipe_domicile_id,
            match_.equipe_exterieur_id,
        ):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Vous ne gérez aucune équipe de ce match.")
        query = query.where(MatchParticipation.club_id == current_user.club_id)
    result = await db.execute(query.order_by(MatchParticipation.id))
    return result.scalars().all()


PHASES_VALIDES = ("poule", "quart", "demi", "finale")


@router.put("/{match_id}/phase", response_model=MatchOut)
async def changer_phase_match(
    match_id: int,
    payload: MatchPhaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    match_ = await verifier_organisateur_du_match(match_id, current_user, db)
    if match_.locked:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Match verrouillé : phase non modifiable.")
    if payload.phase not in PHASES_VALIDES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Phase inconnue : poule, quart, demi ou finale.")
    if payload.phase == "poule":
        if match_.equipe_domicile_id is None or match_.equipe_exterieur_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Les deux équipes sont nécessaires pour une poule.")
        groupe_officiel = await determiner_groupe_match(
            db,
            match_.saison_id,
            match_.equipe_domicile_id,
            match_.equipe_exterieur_id,
            payload.phase,
            payload.groupe,
        )
    else:
        groupe_officiel = getattr(payload.groupe, "value", payload.groupe)
    avant = {"phase": match_.phase, "groupe": match_.groupe}
    match_.phase = payload.phase
    match_.groupe = groupe_officiel
    await log_audit(
        db,
        "matchs",
        match_.id,
        ActionAudit.UPDATE,
        current_user.id,
        avant,
        {"phase": payload.phase, "groupe": groupe_officiel},
    )
    await db.commit()
    await db.refresh(match_)
    return match_


# ==== PACK COMPOSITION (11 sept) : feuille de match numérique ====


def _composition_lignes(formation: str | None) -> list[int] | None:
    """Retourne les capacités des lignes, gardien inclus.

    Les formations de composition doivent décrire exactement onze slots :
    un gardien et dix joueurs de champ. Les indices envoyés par le client
    sont validés contre cette structure, jamais contre le poste habituel.
    """
    slots = slots_formation(formation)
    if slots is None:
        return None
    return [
        max(position for ligne, position in slots if ligne == ligne_index) + 1
        for ligne_index in range(max(ligne for ligne, _ in slots) + 1)
    ]


def _valider_positions_composition(payload: CompositionEquipeIn) -> None:
    """Refuse toute feuille titulaire sans slot explicite et sans doublon."""
    lignes = _composition_lignes(payload.formation)
    if lignes is None:
        raise HTTPException(
            status_code=400,
            detail="Une formation valide avec exactement onze positions est obligatoire pour placer les titulaires.",
        )

    occupes: dict[tuple[int, int], int] = {}
    for ligne in payload.joueurs:
        est_titulaire = _value(ligne.statut) == "titulaire"
        paire = (ligne.ligne_index, ligne.position_index)
        if not est_titulaire:
            if ligne.ligne_index is not None or ligne.position_index is not None:
                raise HTTPException(
                    status_code=400,
                    detail="Un remplaçant ne peut pas occuper une position de titulaire.",
                )
            continue
        if ligne.ligne_index is None or ligne.position_index is None:
            raise HTTPException(
                status_code=400,
                detail="Chaque titulaire doit recevoir une position tactique explicite.",
            )
        if ligne.ligne_index >= len(lignes) or ligne.position_index >= lignes[ligne.ligne_index]:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"La position {ligne.ligne_index}:{ligne.position_index} "
                    "n'existe pas dans la formation choisie."
                ),
            )
        joueur_precedent = occupes.get(paire)
        if joueur_precedent is not None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"La position {ligne.ligne_index}:{ligne.position_index} "
                    f"est déjà occupée par le joueur {joueur_precedent}. "
                    "Aucun joueur n'est déplacé automatiquement."
                ),
            )
        occupes[paire] = ligne.joueur_id

    if len(occupes) != 11:
        raise HTTPException(
            status_code=400,
            detail="Les 11 titulaires doivent occuper 11 positions distinctes de la formation.",
        )


async def _bloc_equipe(db: AsyncSession, match_: Match, equipe: str, max_rempl: int) -> CompositionEquipeOut:
    club_id = match_.equipe_domicile_id if equipe == "domicile" else match_.equipe_exterieur_id
    bloc = CompositionEquipeOut()
    if club_id is None:
        return bloc
    club = await db.get(Club, club_id)
    bloc.club_id = club_id
    bloc.club_nom = club.nom if club else None
    bloc.logo_url = club.logo_url if club else None
    bloc.formation = match_.formation_domicile if equipe == "domicile" else match_.formation_exterieur
    staff_id = match_.staff_domicile_id if equipe == "domicile" else match_.staff_exterieur_id
    if staff_id:
        st = (
            await db.execute(
                select(Staff).where(Staff.id == staff_id).options(selectinload(Staff.photo_actuelle_rel))
            )
        ).scalar_one_or_none()
        if st:
            bloc.staff = CompositionStaffOut(
                id=st.id, nom_complet=st.nom_complet, role=getattr(st.role, "value", st.role), photo_url=st.photo_url
            )
    rows = (
        await db.execute(
            select(MatchParticipation)
            .where(MatchParticipation.match_id == match_.id)
            .where(MatchParticipation.equipe_concernee == equipe)
            .order_by(MatchParticipation.id)
        )
    ).scalars().all()
    ids = [part.joueur_id for part in rows]
    par_id = {}
    if ids:
        js = (
            await db.execute(
                select(Joueur).where(Joueur.id.in_(ids)).options(selectinload(Joueur.photo_actuelle_rel))
            )
        ).scalars().all()
        par_id = {j.id: j for j in js}
    positions_titulaires: set[tuple[int, int]] = set()
    tous_les_titulaires_positionnes = True
    for part in rows:
        j = par_id.get(part.joueur_id)
        if not j:
            tous_les_titulaires_positionnes = False
            continue
        out = CompositionJoueurOut(
            id=j.id,
            nom_complet=j.nom_complet,
            poste=getattr(j.poste, "value", j.poste),
            numero=part.numero if part.numero is not None else getattr(j, "numero", None),
            photo_url=j.photo_url,
            ligne_index=part.ligne_index,
            position_index=part.position_index,
        )
        if getattr(part.statut, "value", part.statut) == "titulaire":
            bloc.titulaires.append(out)
            if part.ligne_index is None or part.position_index is None:
                tous_les_titulaires_positionnes = False
            else:
                positions_titulaires.add((part.ligne_index, part.position_index))
        else:
            bloc.banc.append(out)
    bloc.position_complete = (
        tous_les_titulaires_positionnes
        and len(positions_titulaires) == len(bloc.titulaires)
        and positions_titulaires_valides(bloc.formation, rows)
    )
    return bloc


async def _composition_complete(db: AsyncSession, match_: Match) -> CompositionOut:
    saison = await db.get(Saison, match_.saison_id)
    compo = await db.get(Competition, saison.competition_id) if saison else None
    reglement = await get_reglement_pour_match(db, match_, allow_active_for_new=True)
    regle_compo = (reglement.configuration or {}).get("composition", {}) if reglement else {}
    max_reglement = regle_compo.get("remplacants_max") if isinstance(regle_compo, dict) else None
    max_rempl = max_reglement if max_reglement is not None else (
        compo.max_remplacants if compo and compo.max_remplacants else settings.compo_remplacants_defaut
    )
    return CompositionOut(
        match_id=match_.id,
        max_remplacants=max_rempl,
        domicile=await _bloc_equipe(db, match_, "domicile", max_rempl),
        exterieur=await _bloc_equipe(db, match_, "exterieur", max_rempl),
    )


@router.get("/{match_id}/composition", response_model=CompositionOut)
async def lire_composition(match_id: int, db: AsyncSession = Depends(get_db)):
    match_ = await db.get(Match, match_id)
    if not match_:
        raise HTTPException(status_code=404, detail="Match introuvable.")
    return await _composition_complete(db, match_)


@router.put("/{match_id}/composition", response_model=CompositionOut)
async def enregistrer_composition(
    match_id: int,
    payload: CompositionEquipeIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            RoleUtilisateur.ADMIN,
            RoleUtilisateur.ORGANISATEUR,
            *CLUB_ROLES,
        )
    ),
):
    # Lock the match before reading or changing its team sheet. Two club
    # sessions cannot both pass validation and overwrite one another.
    match_ = await db.scalar(select(Match).where(Match.id == match_id).with_for_update())
    if not match_:
        raise HTTPException(status_code=404, detail="Match introuvable.")
    if not isClubRole(current_user.role):
        await verifier_organisateur_du_match(match_id, current_user, db)
    statut_match = _value(match_.statut)
    if match_.locked or statut_match != StatutMatch.PROGRAMME.value:
        raise HTTPException(status_code=400, detail="Match verrouillé : composition non modifiable.")
    equipe = getattr(payload.equipe, "value", payload.equipe)
    club_id = match_.equipe_domicile_id if equipe == "domicile" else match_.equipe_exterieur_id
    if club_id is None:
        raise HTTPException(status_code=400, detail="Équipe non définie pour ce match.")
    if isClubRole(current_user.role) and current_user.club_id != club_id:
        raise HTTPException(status_code=403, detail="Vous ne gérez pas cette équipe.")
    saison = await db.get(Saison, match_.saison_id)
    compo = await db.get(Competition, saison.competition_id) if saison else None
    reglement = await get_reglement_pour_match(db, match_, allow_active_for_new=True)
    regle_compo = (reglement.configuration or {}).get("composition", {}) if reglement else {}
    max_reglement = regle_compo.get("remplacants_max") if isinstance(regle_compo, dict) else None
    max_rempl = max_reglement if max_reglement is not None else (
        compo.max_remplacants if compo and compo.max_remplacants else settings.compo_remplacants_defaut
    )
    titulaires = [j for j in payload.joueurs if getattr(j.statut, "value", j.statut) == "titulaire"]
    banc = [j for j in payload.joueurs if getattr(j.statut, "value", j.statut) == "remplacant"]
    # Une feuille de football ne peut être enregistrée que si elle contient
    # exactement onze titulaires : ni brouillon incomplet, ni douzième titulaire.
    min_banc = regle_compo.get("remplacants_min") if isinstance(regle_compo, dict) else None
    if len(titulaires) != 11:
        raise HTTPException(status_code=400, detail="La composition doit contenir exactement 11 titulaires.")
    if len(banc) > max_rempl:
        raise HTTPException(status_code=400, detail=f"Maximum {max_rempl} remplaçants pour cette compétition.")
    if min_banc is not None and len(banc) < min_banc:
        raise HTTPException(status_code=400, detail=f"Minimum {min_banc} remplaçants.")
    _valider_positions_composition(payload)

    joueurs_vus: set[int] = set()
    numeros_vus: dict[int, int] = {}
    for ligne in payload.joueurs:
        if ligne.joueur_id in joueurs_vus:
            raise HTTPException(status_code=400, detail="Un même joueur ne peut apparaître qu'une seule fois dans la composition.")
        joueurs_vus.add(ligne.joueur_id)
        if ligne.numero is not None:
            autre_joueur = numeros_vus.get(ligne.numero)
            if autre_joueur is not None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Le numéro {ligne.numero} est attribué à plusieurs joueurs.",
                )
            numeros_vus[ligne.numero] = ligne.joueur_id

    if payload.staff_id:
        st = await db.get(Staff, payload.staff_id)
        if not st or st.club_id != club_id:
            raise HTTPException(status_code=400, detail="Entraîneur hors de ce club.")
    ids_voulus: set[int] = set()
    joueurs_valides: dict[int, Joueur] = {}
    for ligne in payload.joueurs:
        j = await db.get(Joueur, ligne.joueur_id)
        if not j or j.club_actuel_id != club_id:
            raise HTTPException(status_code=400, detail="Un joueur sélectionné n'appartient pas à ce club.")
        eligibilite = await verifier_joueur(db, match_, ligne.joueur_id, club_id, equipe=equipe)
        if eligibilite.statut == "BLOQUANT":
            raise HTTPException(status_code=400, detail=eligibilite.message)
        ids_voulus.add(ligne.joueur_id)
        joueurs_valides[ligne.joueur_id] = j
    avant = {
        "formation": match_.formation_domicile if equipe == "domicile" else match_.formation_exterieur,
        "staff_id": match_.staff_domicile_id if equipe == "domicile" else match_.staff_exterieur_id,
    }
    existantes = (
        await db.execute(
            select(MatchParticipation)
            .where(MatchParticipation.match_id == match_.id)
            .where(MatchParticipation.equipe_concernee == equipe)
            .with_for_update()
        )
    ).scalars().all()
    anciens_joueurs = (
        await db.execute(select(Joueur).where(Joueur.id.in_([part.joueur_id for part in existantes])))
    ).scalars().all() if existantes else []
    joueurs_par_id = {joueur.id: joueur for joueur in anciens_joueurs}
    joueurs_par_id.update(joueurs_valides)
    ancienne_par_joueur = {
        part.joueur_id: {
            "match_id": match_.id,
            "equipe": equipe,
            "joueur_id": part.joueur_id,
            "poste": _value(joueurs_par_id[part.joueur_id].poste)
            if part.joueur_id in joueurs_par_id
            else None,
            "statut": _value(part.statut),
            "numero": part.numero,
            "ligne_index": part.ligne_index,
            "position_index": part.position_index,
        }
        for part in existantes
    }
    for part in existantes:
        if part.joueur_id not in ids_voulus:
            await db.delete(part)
    for ligne in payload.joueurs:
        stat = getattr(ligne.statut, "value", ligne.statut)
        part = next((p for p in existantes if p.joueur_id == ligne.joueur_id), None)
        if part:
            part.statut = stat
            # Une valeur NULL signifie explicitement « numéro non renseigné ».
            # Ne conservons pas silencieusement un ancien numéro lorsque le
            # club l'a effacé dans l'éditeur.
            part.numero = ligne.numero
            part.ligne_index = ligne.ligne_index
            part.position_index = ligne.position_index
        else:
            part = MatchParticipation(
                match_id=match_.id,
                joueur_id=ligne.joueur_id,
                club_id=club_id,
                equipe_concernee=equipe,
                statut=stat,
                minute_entree=0,
                numero=ligne.numero,
                ligne_index=ligne.ligne_index,
                position_index=ligne.position_index,
            )
            db.add(part)
            existantes.append(part)
    await db.flush()
    # One append-only audit row per player, including the effective user id
    # through log_audit: added, removed, and all composition attributes.
    for joueur_id, ancien in ancienne_par_joueur.items():
        if joueur_id not in ids_voulus:
            await log_audit(
                db,
                "match_compositions",
                next(p.id for p in existantes if p.joueur_id == joueur_id),
                ActionAudit.DELETE,
                current_user.id,
                ancien,
                None,
            )
    for ligne in payload.joueurs:
        part = next(p for p in existantes if p.joueur_id == ligne.joueur_id)
        joueur = joueurs_valides[ligne.joueur_id]
        nouveau = {
            "match_id": match_.id,
            "equipe": equipe,
            "joueur_id": joueur.id,
            "poste": _value(joueur.poste),
            "statut": _value(ligne.statut),
            "numero": ligne.numero,
            "ligne_index": ligne.ligne_index,
            "position_index": ligne.position_index,
        }
        await log_audit(
            db,
            "match_compositions",
            part.id,
            ActionAudit.INSERT if ligne.joueur_id not in ancienne_par_joueur else ActionAudit.UPDATE,
            current_user.id,
            ancienne_par_joueur.get(ligne.joueur_id),
            nouveau,
        )
    if equipe == "domicile":
        match_.formation_domicile = payload.formation
        match_.staff_domicile_id = payload.staff_id
    else:
        match_.formation_exterieur = payload.formation
        match_.staff_exterieur_id = payload.staff_id
    apres = {
        "formation": payload.formation,
        "staff_id": payload.staff_id,
        "titulaires": len(titulaires),
        "banc": len(banc),
        "positions_complete": True,
    }
    await log_audit(db, "matchs", match_.id, ActionAudit.UPDATE, current_user.id, avant, apres)
    await db.commit()
    await db.refresh(match_)
    return await _composition_complete(db, match_)
