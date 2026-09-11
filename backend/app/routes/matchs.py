from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.rbac import require_roles, verifier_organisateur_de_competition, verifier_organisateur_du_match
from app.config import settings
from app.database import get_db
from app.models.competition import Saison, SaisonClub
from app.models.enums import ActionAudit, EquipeConcernee, PeriodeMatch, RoleUtilisateur, StatutMatch
from app.models.joueur import Joueur
from app.models.match import Match, MatchParticipation
from app.models.user import User
from app.schemas.match import MatchCreate, MatchOut, MatchPhaseUpdate, ParticipationCreate, ParticipationOut, ParticipationUpdate
from app.services.audit import log_audit
from app.schemas.match import (
    CompositionEquipeIn,
    CompositionEquipeOut,
    CompositionJoueurOut,
    CompositionOut,
    CompositionStaffOut,
)
from app.models.club import Club
from app.models.competition import Competition
from app.models.staff import Staff
from app.services.validation import valider_match

router = APIRouter(prefix="/matchs", tags=["Matchs"])


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
            StatutMatch.PROGRAMME,
            StatutMatch.EN_COURS,
            StatutMatch.TERMINE,
            StatutMatch.VALIDE,
        ])
    )
    if saison_id:
        query = query.where(Match.saison_id == saison_id)
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
    statut = match_.statut.value if match_ and hasattr(match_.statut, "value") else match_.statut
    if match_ is None or statut not in ("programme", "en_cours", "termine", "valide"):
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

    inscrits = await db.execute(
        select(SaisonClub.club_id).where(SaisonClub.saison_id == payload.saison_id)
    )
    club_ids = {row[0] for row in inscrits.all()}
    if payload.equipe_domicile_id not in club_ids or payload.equipe_exterieur_id not in club_ids:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Les deux équipes doivent être inscrites à cette saison.",
        )

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
    await log_audit(db, "matchs", match_.id, ActionAudit.UPDATE, current_user.id, {"statut": old_statut}, {"statut": nouveau_statut.value})
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


PHASES_VALIDES = ("poule", "quart", "demi", "finale")


@router.put("/{match_id}/phase", response_model=MatchOut)
async def changer_phase_match(
    match_id: int,
    payload: MatchPhaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    match_ = await db.get(Match, match_id)
    if match_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    if match_.locked:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Match verrouillé : phase non modifiable.")
    if payload.phase not in PHASES_VALIDES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Phase inconnue : poule, quart, demi ou finale.")
    if payload.groupe is not None and len(payload.groupe) > 2:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Groupe : une ou deux lettres.")
    avant = {"phase": match_.phase, "groupe": match_.groupe}
    match_.phase = payload.phase
    match_.groupe = payload.groupe
    await log_audit(db, "matchs", match_.id, ActionAudit.UPDATE, current_user.id, avant, payload.model_dump())
    await db.commit()
    await db.refresh(match_)
    return match_


# ==== PACK COMPOSITION (11 sept) : feuille de match numérique ====


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
        st = await db.get(Staff, staff_id)
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
    for part in rows:
        j = await db.get(Joueur, part.joueur_id)
        if not j:
            continue
        out = CompositionJoueurOut(
            id=j.id,
            nom_complet=j.nom_complet,
            poste=getattr(j.poste, "value", j.poste),
            numero=part.numero if part.numero is not None else getattr(j, "numero", None),
            photo_url=j.photo_url,
        )
        if getattr(part.statut, "value", part.statut) == "titulaire":
            bloc.titulaires.append(out)
        else:
            bloc.banc.append(out)
    return bloc


async def _composition_complete(db: AsyncSession, match_: Match) -> CompositionOut:
    saison = await db.get(Saison, match_.saison_id)
    compo = await db.get(Competition, saison.competition_id) if saison else None
    max_rempl = (compo.max_remplacants if compo and compo.max_remplacants else settings.compo_remplacants_defaut)
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
            RoleUtilisateur.CLUB_MANAGER,
            RoleUtilisateur.COACH,
        )
    ),
):
    match_ = await db.get(Match, match_id)
    if not match_:
        raise HTTPException(status_code=404, detail="Match introuvable.")
    if match_.locked or getattr(match_.statut, "value", match_.statut) in ("termine", "valide"):
        raise HTTPException(status_code=400, detail="Match verrouillé : composition non modifiable.")
    equipe = getattr(payload.equipe, "value", payload.equipe)
    club_id = match_.equipe_domicile_id if equipe == "domicile" else match_.equipe_exterieur_id
    if club_id is None:
        raise HTTPException(status_code=400, detail="Équipe non définie pour ce match.")
    role = getattr(current_user.role, "value", current_user.role)
    if role in ("club_manager", "coach") and current_user.club_id != club_id:
        raise HTTPException(status_code=403, detail="Vous ne gérez pas cette équipe.")
    saison = await db.get(Saison, match_.saison_id)
    compo = await db.get(Competition, saison.competition_id) if saison else None
    max_rempl = (compo.max_remplacants if compo and compo.max_remplacants else settings.compo_remplacants_defaut)
    titulaires = [j for j in payload.joueurs if getattr(j.statut, "value", j.statut) == "titulaire"]
    banc = [j for j in payload.joueurs if getattr(j.statut, "value", j.statut) == "remplacant"]
    if len(titulaires) > 11:
        raise HTTPException(status_code=400, detail="Maximum 11 titulaires.")
    if len(banc) > max_rempl:
        raise HTTPException(status_code=400, detail=f"Maximum {max_rempl} remplaçants pour cette compétition.")
    if payload.staff_id:
        st = await db.get(Staff, payload.staff_id)
        if not st or st.club_id != club_id:
            raise HTTPException(status_code=400, detail="Entraîneur hors de ce club.")
    ids_voulus = set()
    for ligne in payload.joueurs:
        j = await db.get(Joueur, ligne.joueur_id)
        if not j or j.club_actuel_id != club_id:
            raise HTTPException(status_code=400, detail="Un joueur sélectionné n'appartient pas à ce club.")
        ids_voulus.add(ligne.joueur_id)
    avant = {
        "formation": match_.formation_domicile if equipe == "domicile" else match_.formation_exterieur,
        "staff_id": match_.staff_domicile_id if equipe == "domicile" else match_.staff_exterieur_id,
    }
    existantes = (
        await db.execute(
            select(MatchParticipation)
            .where(MatchParticipation.match_id == match_.id)
            .where(MatchParticipation.equipe_concernee == equipe)
        )
    ).scalars().all()
    par_joueur = {p.joueur_id: p for p in existantes}
    for part in existantes:
        if part.joueur_id not in ids_voulus:
            await db.delete(part)
    for ligne in payload.joueurs:
        stat = getattr(ligne.statut, "value", ligne.statut)
        part = par_joueur.get(ligne.joueur_id)
        if part:
            part.statut = stat
            if ligne.numero is not None:
                part.numero = ligne.numero
        else:
            db.add(
                MatchParticipation(
                    match_id=match_.id,
                    joueur_id=ligne.joueur_id,
                    club_id=club_id,
                    equipe_concernee=equipe,
                    statut=stat,
                    minute_entree=0,
                    numero=ligne.numero,
                )
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
    }
    await log_audit(db, "matchs", match_.id, ActionAudit.UPDATE, current_user.id, avant, apres)
    await db.commit()
    await db.refresh(match_)
    return await _composition_complete(db, match_)
