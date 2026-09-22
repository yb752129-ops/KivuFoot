"""Service transactionnel de Possession V1.

Le service ne connaît que le chronomètre observé. Aucun événement de match
n'est lu pour produire les durées. Toutes les écritures sont faites dans la
transaction de l'appelant et chaque commande porte un UUID idempotent.
"""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.club import Club
from app.models.enums import (
    ActionAudit,
    EtatPossession,
    MethodePossession,
    PeriodeMatch,
    ProtocolePossession,
    StatutMatch,
    StatutPossession,
)
from app.models.match import Match
from app.models.possession import PossessionCorrection, PossessionIntervalle, PossessionMatch, PossessionOperation
from app.schemas.possession import PossessionDetailOut, PossessionIntervalleOut, PossessionPublicOut
from app.services.audit import log_audit

_TEAM_STATES = {EtatPossession.TEAM_A, EtatPossession.TEAM_B}


def _value(value):
    return value.value if hasattr(value, "value") else value


def _as_utc(value: datetime) -> datetime:
    """SQLite peut rendre un DateTime timezone=True naïf : l'interpréter en UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _duration_ms(start: datetime, end: datetime) -> int:
    duration = int((_as_utc(end) - _as_utc(start)).total_seconds() * 1000)
    if duration < 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Horodatage de possession incohérent : une durée négative est impossible.",
        )
    return duration


def _match_status(match: Match) -> str:
    return _value(match.statut)


def _state(value) -> EtatPossession:
    try:
        return value if isinstance(value, EtatPossession) else EtatPossession(value)
    except (TypeError, ValueError):
        raise HTTPException(status.HTTP_409_CONFLICT, "État de possession incohérent en base.")


async def get_possession(db: AsyncSession, match_id: int) -> PossessionMatch | None:
    result = await db.execute(select(PossessionMatch).where(PossessionMatch.match_id == match_id))
    return result.scalar_one_or_none()


async def _locked_match(db: AsyncSession, match_id: int) -> Match:
    result = await db.execute(select(Match).where(Match.id == match_id).with_for_update())
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    return match


async def _locked_possession(db: AsyncSession, match_id: int) -> PossessionMatch | None:
    result = await db.execute(
        select(PossessionMatch).where(PossessionMatch.match_id == match_id).with_for_update()
    )
    return result.scalar_one_or_none()


async def _operation_deja_recue(db: AsyncSession, operation_id: uuid.UUID) -> PossessionOperation | None:
    result = await db.execute(
        select(PossessionOperation).where(PossessionOperation.operation_id == operation_id)
    )
    return result.scalar_one_or_none()


async def _creer_capture(db: AsyncSession, match: Match, user_id: int) -> PossessionMatch:
    if match.equipe_domicile_id is None or match.equipe_exterieur_id is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Les deux équipes du match sont nécessaires pour chronométrer la possession.",
        )
    possession = PossessionMatch(
        match_id=match.id,
        equipe_a_id=match.equipe_domicile_id,
        equipe_b_id=match.equipe_exterieur_id,
        methode=MethodePossession.TIME_BASED,
        protocole=ProtocolePossession.KIVUFOOT_POSSESSION_V1,
        etat_courant=EtatPossession.NOT_STARTED,
        statut=StatutPossession.PROVISOIRE,
        collecteur_id=user_id,
    )
    db.add(possession)
    await db.flush()
    return possession


async def _get_open_intervals(db: AsyncSession, possession_id: int) -> list[PossessionIntervalle]:
    result = await db.execute(
        select(PossessionIntervalle)
        .where(
            PossessionIntervalle.possession_id == possession_id,
            PossessionIntervalle.fin_at.is_(None),
        )
        .order_by(PossessionIntervalle.id)
        .with_for_update()
    )
    return list(result.scalars().all())


async def _next_sequence(db: AsyncSession, possession_id: int) -> int:
    result = await db.execute(
        select(func.coalesce(func.max(PossessionIntervalle.sequence_no), 0)).where(
            PossessionIntervalle.possession_id == possession_id
        )
    )
    return int(result.scalar_one()) + 1


async def _ouvrir_intervalle(
    db: AsyncSession,
    match: Match,
    possession: PossessionMatch,
    etat: EtatPossession,
    debut_at: datetime,
    user_id: int,
) -> PossessionIntervalle:
    if etat not in (EtatPossession.TEAM_A, EtatPossession.TEAM_B, EtatPossession.PAUSE):
        raise HTTPException(status.HTTP_409_CONFLICT, "Seuls A, B ou PAUSE peuvent ouvrir un intervalle.")
    if await _get_open_intervals(db, possession.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Un chronomètre de possession est déjà ouvert.")
    intervalle = PossessionIntervalle(
        possession_id=possession.id,
        etat=etat,
        sequence_no=await _next_sequence(db, possession.id),
        debut_at=debut_at,
        periode=_value(match.periode) if match.periode is not None else None,
        cree_par_id=user_id,
    )
    db.add(intervalle)
    if etat == EtatPossession.TEAM_A:
        possession.nombre_sequences_a += 1
    elif etat == EtatPossession.TEAM_B:
        possession.nombre_sequences_b += 1
    possession.etat_courant = etat
    possession.pause_hors_jeu = False
    possession.derniere_transition_at = debut_at
    await db.flush()
    return intervalle


async def _fermer_intervalle(
    db: AsyncSession,
    possession: PossessionMatch,
    etat_attendu: EtatPossession,
    fin_at: datetime,
) -> PossessionIntervalle | None:
    ouverts = await _get_open_intervals(db, possession.id)
    courant = _state(possession.etat_courant)
    if courant != etat_attendu:
        raise HTTPException(status.HTTP_409_CONFLICT, "L'état courant et l'intervalle ouvert ne correspondent pas.")
    if len(ouverts) != 1:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "État impossible : il doit exister exactement un intervalle ouvert.",
        )
    intervalle = ouverts[0]
    if _state(intervalle.etat) != etat_attendu:
        raise HTTPException(status.HTTP_409_CONFLICT, "L'intervalle ouvert ne correspond pas à l'état courant.")
    duree = _duration_ms(intervalle.debut_at, fin_at)
    intervalle.fin_at = fin_at
    intervalle.duree_ms = duree
    if etat_attendu == EtatPossession.TEAM_A:
        possession.temps_a_ms += duree
    elif etat_attendu == EtatPossession.TEAM_B:
        possession.temps_b_ms += duree
    elif etat_attendu == EtatPossession.PAUSE:
        possession.temps_non_attribue_ms += duree
    return intervalle


def _normaliser_demande(etat) -> EtatPossession:
    try:
        return etat if isinstance(etat, EtatPossession) else EtatPossession(etat)
    except (TypeError, ValueError):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "État de possession inconnu.")


def _verifier_match_pour_etat(match: Match, courant: EtatPossession, demande: EtatPossession) -> None:
    statut = _match_status(match)
    if match.locked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Match verrouillé : la possession est immuable.")

    if demande in (EtatPossession.TEAM_A, EtatPossession.TEAM_B, EtatPossession.PAUSE):
        if match.forfait:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "La possession V1 n'est pas collectée pour un forfait.",
            )
        if statut != StatutMatch.EN_COURS.value:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Le chronomètre de possession ne fonctionne que pendant un match en cours.",
            )
        if _value(match.periode) == PeriodeMatch.MI_TEMPS.value and demande in _TEAM_STATES:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Mi-temps : la reprise exige d'abord la fin de la pause puis une sélection explicite A ou B.",
            )
    elif demande == EtatPossession.FINISHED:
        if courant == EtatPossession.NOT_STARTED and statut not in (
            StatutMatch.EN_COURS.value,
            StatutMatch.TERMINE.value,
            StatutMatch.VALIDE.value,
        ):
            raise HTTPException(status.HTTP_409_CONFLICT, "Un match non commencé ne peut pas être terminé.")
    elif demande == EtatPossession.NOT_STARTED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "NOT_STARTED est un état initial, pas une commande.")


async def _appliquer_transition_verrouillee(
    db: AsyncSession,
    match: Match,
    possession: PossessionMatch,
    demande: EtatPossession,
    user_id: int,
    operation_id: uuid.UUID,
    now: datetime,
    correction: bool = False,
) -> PossessionMatch:
    now = _as_utc(now)
    courant = _state(possession.etat_courant)
    _verifier_match_pour_etat(match, courant, demande)

    if courant == EtatPossession.FINISHED and demande != EtatPossession.FINISHED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Une possession terminée ne peut plus recevoir de séquence.")
    if courant == EtatPossession.NOT_STARTED and demande == EtatPossession.PAUSE:
        raise HTTPException(status.HTTP_409_CONFLICT, "PAUSE n'est possible qu'après le début du chronomètre.")

    if demande != courant:
        pause_hors_jeu = bool(possession.pause_hors_jeu)
        if courant in (EtatPossession.TEAM_A, EtatPossession.TEAM_B, EtatPossession.PAUSE):
            # Après la mi-temps, PAUSE n'a pas de chronomètre ouvert : le
            # temps de repos est suspendu, il n'entre pas dans le non-attribué.
            if not (courant == EtatPossession.PAUSE and pause_hors_jeu):
                await _fermer_intervalle(db, possession, courant, now)
                # Les sessions de production ont autoflush=False : rendre la
                # fermeture visible avant de vérifier qu'un nouvel intervalle
                # peut être ouvert.
                await db.flush()
        if courant in _TEAM_STATES and demande in _TEAM_STATES and courant != demande:
            possession.nombre_changements += 1
        if demande in (EtatPossession.TEAM_A, EtatPossession.TEAM_B, EtatPossession.PAUSE):
            await _ouvrir_intervalle(db, match, possession, demande, now, user_id)
        else:
            possession.etat_courant = demande
            possession.pause_hors_jeu = False
            possession.derniere_transition_at = now
    else:
        # Même bouton = maintien idempotent : aucune nouvelle séquence et
        # aucun second chronomètre. Une PAUSE de mi-temps n'a volontairement
        # pas d'intervalle ouvert ; une PAUSE terrain en a exactement un.
        if courant in (EtatPossession.TEAM_A, EtatPossession.TEAM_B):
            ouverts = await _get_open_intervals(db, possession.id)
            if len(ouverts) != 1:
                raise HTTPException(status.HTTP_409_CONFLICT, "État impossible : chronomètre ouvert absent ou multiple.")
        elif courant == EtatPossession.PAUSE and not possession.pause_hors_jeu:
            ouverts = await _get_open_intervals(db, possession.id)
            if len(ouverts) != 1:
                raise HTTPException(status.HTTP_409_CONFLICT, "État impossible : pause ouverte absente ou multiple.")
        possession.derniere_transition_at = now

    operation = PossessionOperation(
        possession_id=possession.id,
        operation_id=operation_id,
        etat_demande=demande,
        etat_avant=courant,
        etat_apres=demande,
        appliquee_at=now,
        cree_par_id=user_id,
        correction=correction,
    )
    db.add(operation)
    await db.flush()
    await log_audit(
        db,
        table_name="possessions_matchs",
        record_id=possession.id,
        action=ActionAudit.UPDATE,
        user_id=user_id,
        old_data={"etat_courant": courant.value, "statut": _value(possession.statut)},
        new_data={
            "etat_courant": demande.value,
            "operation_id": str(operation_id),
            "correction": correction,
        },
    )
    return possession


async def transition_possession(
    db: AsyncSession,
    match_id: int,
    demande,
    user_id: int,
    operation_id: uuid.UUID,
    *,
    now: datetime | None = None,
    correction: bool = False,
) -> PossessionMatch:
    """Applique une commande A/B/PAUSE/FINISHED dans une transaction appelante."""
    demande = _normaliser_demande(demande)
    now = _as_utc(now or datetime.now(timezone.utc))

    deja = await _operation_deja_recue(db, operation_id)
    if deja is not None:
        possession = await db.get(PossessionMatch, deja.possession_id)
        if possession is None or possession.match_id != match_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Cette opération a déjà été utilisée pour un autre match.")
        return possession

    match = await _locked_match(db, match_id)
    # Deux mobiles peuvent envoyer le même UUID en parallèle. Le verrou du
    # match sérialise la création, puis cette seconde lecture évite toute
    # violation d'unicité sur possession_operations.
    deja = await _operation_deja_recue(db, operation_id)
    if deja is not None:
        possession = await db.get(PossessionMatch, deja.possession_id)
        if possession is None or possession.match_id != match_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Cette opération a déjà été utilisée pour un autre match.")
        return possession

    possession = await _locked_possession(db, match_id)
    if possession is None:
        if demande == EtatPossession.FINISHED:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Aucune possession n'a démarré : TERMINER ne crée pas une capture fictive.",
            )
        possession = await _creer_capture(db, match, user_id)
    else:
        # Une capture officielle ou un match verrouillé est immuable, même
        # si l'appelant essaie de réutiliser un autre UUID.
        if _value(possession.statut) == StatutPossession.OFFICIELLE.value:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Cette possession est officiellement validée et immuable.")

    await _appliquer_transition_verrouillee(
        db, match, possession, demande, user_id, operation_id, now, correction=correction
    )
    return possession


async def suspendre_possession(
    db: AsyncSession, match_id: int, user_id: int | None, *, now: datetime | None = None
) -> None:
    """Suspend automatiquement le chronomètre lors de la mi-temps.

    La mi-temps ferme le contrôle en cours mais n'ouvre pas une pause
    chronométrée : le repos n'est ni du temps A/B ni une incertitude de jeu.
    """
    possession = await get_possession(db, match_id)
    if possession is None:
        return
    if _state(possession.etat_courant) == EtatPossession.PAUSE and possession.pause_hors_jeu:
        return
    if _state(possession.etat_courant) not in _TEAM_STATES and _state(possession.etat_courant) != EtatPossession.PAUSE:
        return
    operation_id = uuid.uuid5(uuid.NAMESPACE_URL, f"kivufoot:possession:mi-temps:{possession.id}")
    if await _operation_deja_recue(db, operation_id):
        return
    now = _as_utc(now or datetime.now(timezone.utc))
    match = await _locked_match(db, match_id)
    possession = await _locked_possession(db, match_id)
    if possession is None:
        return
    courant = _state(possession.etat_courant)
    if courant == EtatPossession.PAUSE and possession.pause_hors_jeu:
        return
    if courant not in _TEAM_STATES and courant != EtatPossession.PAUSE:
        return
    if courant in _TEAM_STATES or not possession.pause_hors_jeu:
        await _fermer_intervalle(db, possession, courant, now)
        await db.flush()
    possession.etat_courant = EtatPossession.PAUSE
    possession.pause_hors_jeu = True
    possession.derniere_transition_at = now
    operation = PossessionOperation(
        possession_id=possession.id,
        operation_id=operation_id,
        etat_demande=EtatPossession.PAUSE,
        etat_avant=courant,
        etat_apres=EtatPossession.PAUSE,
        appliquee_at=now,
        cree_par_id=user_id or 0,
    )
    db.add(operation)
    await db.flush()
    await log_audit(
        db,
        table_name="possessions_matchs",
        record_id=possession.id,
        action=ActionAudit.UPDATE,
        user_id=user_id,
        old_data={"etat_courant": courant.value},
        new_data={"etat_courant": EtatPossession.PAUSE.value, "motif": "mi_temps", "operation_id": str(operation_id)},
    )


async def terminer_possession(
    db: AsyncSession,
    match_id: int,
    user_id: int | None,
    *,
    now: datetime | None = None,
    exclusion_reason: str | None = None,
) -> None:
    """Ferme la capture à la fin normale ; ne crée jamais de capture vide."""
    possession = await get_possession(db, match_id)
    if possession is None:
        return
    if _state(possession.etat_courant) == EtatPossession.FINISHED:
        if exclusion_reason and possession.eligible_public:
            possession.eligible_public = False
            possession.motif_exclusion_public = exclusion_reason
            await log_audit(
                db,
                table_name="possessions_matchs",
                record_id=possession.id,
                action=ActionAudit.UPDATE,
                user_id=user_id,
                old_data={"eligible_public": True},
                new_data={"eligible_public": False, "motif_exclusion_public": exclusion_reason},
            )
        return
    operation_id = uuid.uuid5(uuid.NAMESPACE_URL, f"kivufoot:possession:fin:{possession.id}")
    await transition_possession(
        db,
        match_id,
        EtatPossession.FINISHED,
        user_id or 0,
        operation_id,
        now=now,
    )
    if exclusion_reason:
        possession.eligible_public = False
        possession.motif_exclusion_public = exclusion_reason
        await log_audit(
            db,
            table_name="possessions_matchs",
            record_id=possession.id,
            action=ActionAudit.UPDATE,
            user_id=user_id,
            old_data={"eligible_public": True},
            new_data={"eligible_public": False, "motif_exclusion_public": exclusion_reason},
        )


async def corriger_intervalle_possession(
    db: AsyncSession,
    match_id: int,
    intervalle_id: int,
    nouvel_etat,
    user_id: int,
    operation_id: uuid.UUID,
    motif: str,
    *,
    debut_at: datetime | None = None,
    fin_at: datetime | None = None,
) -> PossessionMatch:
    """Corrige un intervalle fermé sans effacer sa valeur précédente.

    La ligne courante est mise à jour, mais l'ancienne valeur, le motif,
    l'auteur et l'UUID de commande restent dans possession_corrections et
    dans l'audit. Une correction ne peut pas rouvrir un chronomètre.
    """
    nouvel_etat = _normaliser_demande(nouvel_etat)
    if nouvel_etat not in (EtatPossession.TEAM_A, EtatPossession.TEAM_B, EtatPossession.PAUSE):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Une correction porte sur A, B ou PAUSE.")
    if not motif or len(motif.strip()) < 10:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Un motif de correction détaillé est obligatoire.")

    deja = await db.execute(
        select(PossessionCorrection).where(PossessionCorrection.operation_id == operation_id)
    )
    correction_existante = deja.scalar_one_or_none()
    if correction_existante is not None:
        possession = await db.get(PossessionMatch, correction_existante.possession_id)
        if possession is None or possession.match_id != match_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Cette correction a déjà été utilisée pour un autre match.")
        return possession

    match = await _locked_match(db, match_id)
    possession = await _locked_possession(db, match_id)
    if possession is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucune possession n'est enregistrée pour ce match.")
    if match.locked or _value(possession.statut) == StatutPossession.OFFICIELLE.value:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Une possession officielle ou verrouillée ne peut plus être corrigée.")

    intervalle_result = await db.execute(
        select(PossessionIntervalle)
        .where(
            PossessionIntervalle.id == intervalle_id,
            PossessionIntervalle.possession_id == possession.id,
        )
        .with_for_update()
    )
    intervalle = intervalle_result.scalar_one_or_none()
    if intervalle is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Intervalle de possession introuvable.")
    if intervalle.fin_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Fermez l'intervalle avant de le corriger.")

    ancien_etat = _state(intervalle.etat)
    ancien_debut = _as_utc(intervalle.debut_at)
    ancien_fin = _as_utc(intervalle.fin_at)
    nouveau_debut = _as_utc(debut_at or ancien_debut)
    nouveau_fin = _as_utc(fin_at or ancien_fin)
    nouvelle_duree = _duration_ms(nouveau_debut, nouveau_fin)

    voisins = await db.execute(
        select(PossessionIntervalle)
        .where(PossessionIntervalle.possession_id == possession.id)
        .order_by(PossessionIntervalle.id)
    )
    lignes = list(voisins.scalars().all())
    position = next((index for index, ligne in enumerate(lignes) if ligne.id == intervalle.id), None)
    if position is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Intervalle de possession introuvable.")
    precedent = lignes[position - 1] if position else None
    suivant = lignes[position + 1] if position + 1 < len(lignes) else None
    if precedent and precedent.fin_at and _as_utc(precedent.fin_at) > nouveau_debut:
        raise HTTPException(status.HTTP_409_CONFLICT, "La correction chevauche l'intervalle précédent.")
    if suivant and _as_utc(suivant.debut_at) < nouveau_fin:
        raise HTTPException(status.HTTP_409_CONFLICT, "La correction chevauche l'intervalle suivant.")

    correction = PossessionCorrection(
        possession_id=possession.id,
        intervalle_id=intervalle.id,
        operation_id=operation_id,
        ancien_etat=ancien_etat,
        ancien_debut_at=ancien_debut,
        ancien_fin_at=ancien_fin,
        ancien_duree_ms=int(intervalle.duree_ms or 0),
        nouvel_etat=nouvel_etat,
        nouveau_debut_at=nouveau_debut,
        nouveau_fin_at=nouveau_fin,
        nouvelle_duree_ms=nouvelle_duree,
        motif=motif.strip(),
        corrige_par_id=user_id,
    )
    db.add(correction)
    intervalle.etat = nouvel_etat
    intervalle.debut_at = nouveau_debut
    intervalle.fin_at = nouveau_fin
    intervalle.duree_ms = nouvelle_duree
    await db.flush()

    # Les compteurs sont reconstruits à partir des intervalles conservés ;
    # aucune durée ne provient des événements sportifs.
    temps_a = temps_b = temps_pause = sequences_a = sequences_b = changements = 0
    precedent_etat = None
    for ligne in lignes:
        etat_ligne = _state(ligne.etat)
        duree_ligne = int(ligne.duree_ms or 0)
        if etat_ligne == EtatPossession.TEAM_A:
            temps_a += duree_ligne
            sequences_a += 1
        elif etat_ligne == EtatPossession.TEAM_B:
            temps_b += duree_ligne
            sequences_b += 1
        else:
            temps_pause += duree_ligne
        if precedent_etat in _TEAM_STATES and etat_ligne in _TEAM_STATES and precedent_etat != etat_ligne:
            changements += 1
        precedent_etat = etat_ligne
    possession.temps_a_ms = temps_a
    possession.temps_b_ms = temps_b
    possession.temps_non_attribue_ms = temps_pause
    possession.nombre_sequences_a = sequences_a
    possession.nombre_sequences_b = sequences_b
    possession.nombre_changements = changements
    await db.flush()
    await log_audit(
        db,
        table_name="possessions_matchs",
        record_id=possession.id,
        action=ActionAudit.UPDATE,
        user_id=user_id,
        old_data={
            "intervalle_id": intervalle.id,
            "etat": ancien_etat.value,
            "debut_at": ancien_debut.isoformat(),
            "fin_at": ancien_fin.isoformat(),
            "duree_ms": int(correction.ancien_duree_ms),
        },
        new_data={
            "correction_id": correction.id,
            "operation_id": str(operation_id),
            "etat": nouvel_etat.value,
            "debut_at": nouveau_debut.isoformat(),
            "fin_at": nouveau_fin.isoformat(),
            "duree_ms": nouvelle_duree,
            "motif": motif.strip(),
        },
    )
    return possession


async def officialiser_possession(db: AsyncSession, match_id: int, user_id: int) -> None:
    """Rend la capture publique uniquement avec un match officiellement validé."""
    possession = await get_possession(db, match_id)
    if possession is None:
        return
    if _state(possession.etat_courant) != EtatPossession.FINISHED:
        # Le match peut être validé sans avoir collecté de possession ou si
        # le collecteur a oublié TERMINER : aucune officialisation implicite.
        return
    if _value(possession.statut) == StatutPossession.OFFICIELLE.value:
        return
    possession.statut = StatutPossession.OFFICIELLE
    possession.valide_par_id = user_id
    possession.officialisee_at = datetime.now(timezone.utc)
    await db.flush()
    await log_audit(
        db,
        table_name="possessions_matchs",
        record_id=possession.id,
        action=ActionAudit.VALIDATE,
        user_id=user_id,
        old_data={"statut": StatutPossession.PROVISOIRE.value},
        new_data={"statut": StatutPossession.OFFICIELLE.value},
    )


async def _noms_equipes(db: AsyncSession, match: Match) -> tuple[str | None, str | None]:
    a = await db.get(Club, match.equipe_domicile_id) if match.equipe_domicile_id else None
    b = await db.get(Club, match.equipe_exterieur_id) if match.equipe_exterieur_id else None
    return (a.nom if a else None, b.nom if b else None)


async def snapshot_possession(
    db: AsyncSession,
    match: Match,
    possession: PossessionMatch | None,
    *,
    now: datetime | None = None,
    include_intervals: bool = True,
) -> PossessionDetailOut:
    """Construit un état de lecture ; le temps de l'intervalle ouvert est live."""
    now = _as_utc(now or datetime.now(timezone.utc))
    equipe_a_nom, equipe_b_nom = await _noms_equipes(db, match)
    if possession is None:
        return PossessionDetailOut(
            id=None,
            match_id=match.id,
            equipe_a_id=match.equipe_domicile_id,
            equipe_b_id=match.equipe_exterieur_id,
            equipe_a_nom=equipe_a_nom,
            equipe_b_nom=equipe_b_nom,
            methode=MethodePossession.TIME_BASED,
            protocole=ProtocolePossession.KIVUFOOT_POSSESSION_V1,
            etat_courant=EtatPossession.NOT_STARTED,
            statut=StatutPossession.PROVISOIRE,
            message="Possession non disponible",
            est_disponible=False,
        )

    etat = _state(possession.etat_courant)
    a = int(possession.temps_a_ms or 0)
    b = int(possession.temps_b_ms or 0)
    non = int(possession.temps_non_attribue_ms or 0)
    ouvert_depuis = None
    if etat in (EtatPossession.TEAM_A, EtatPossession.TEAM_B, EtatPossession.PAUSE):
        ouverts = await db.execute(
            select(PossessionIntervalle)
            .where(
                PossessionIntervalle.possession_id == possession.id,
                PossessionIntervalle.fin_at.is_(None),
            )
            .order_by(desc(PossessionIntervalle.id))
        )
        intervalle = ouverts.scalars().first()
        if intervalle:
            ouvert_depuis = _as_utc(intervalle.debut_at)
            live = _duration_ms(intervalle.debut_at, now)
            if etat == EtatPossession.TEAM_A:
                a += live
            elif etat == EtatPossession.TEAM_B:
                b += live
            else:
                non += live

    mesure = a + b
    pct_a = None
    pct_b = None
    if mesure > 0:
        pct_a = int((a * 100 / mesure) + 0.5)
        pct_b = 100 - pct_a

    intervals_out: list[PossessionIntervalleOut] = []
    if include_intervals:
        result = await db.execute(
            select(PossessionIntervalle)
            .where(PossessionIntervalle.possession_id == possession.id)
            .order_by(PossessionIntervalle.id)
        )
        for intervalle in result.scalars().all():
            duree = int(intervalle.duree_ms or 0)
            if intervalle.fin_at is None:
                duree = _duration_ms(intervalle.debut_at, now)
            intervals_out.append(
                PossessionIntervalleOut(
                    id=intervalle.id,
                    etat=_state(intervalle.etat),
                    sequence_no=intervalle.sequence_no,
                    debut_at=_as_utc(intervalle.debut_at),
                    fin_at=_as_utc(intervalle.fin_at) if intervalle.fin_at else None,
                    duree_ms=duree,
                    duree_secondes=round(duree / 1000, 3),
                    periode=intervalle.periode,
                    cree_par_id=intervalle.cree_par_id,
                )
            )

    disponible = mesure > 0 and _value(possession.statut) == StatutPossession.OFFICIELLE.value and possession.eligible_public
    message = None if disponible else (
        "Possession non disponible"
        if mesure <= 0 or _value(possession.statut) != StatutPossession.OFFICIELLE.value or not possession.eligible_public
        else "Possession non disponible"
    )
    return PossessionDetailOut(
        id=possession.id,
        match_id=match.id,
        equipe_a_id=possession.equipe_a_id,
        equipe_b_id=possession.equipe_b_id,
        equipe_a_nom=equipe_a_nom,
        equipe_b_nom=equipe_b_nom,
        methode=_value(possession.methode),
        protocole=_value(possession.protocole),
            etat_courant=etat,
            pause_hors_jeu=bool(possession.pause_hors_jeu),
            statut=_value(possession.statut),
        temps_a=round(a / 1000, 3),
        temps_b=round(b / 1000, 3),
        temps_non_attribue=round(non / 1000, 3),
        temps_a_ms=a,
        temps_b_ms=b,
        temps_non_attribue_ms=non,
        temps_a_secondes=round(a / 1000, 3),
        temps_b_secondes=round(b / 1000, 3),
        temps_non_attribue_secondes=round(non / 1000, 3),
        temps_mesure_ms=mesure,
        pourcentage_a=pct_a,
        pourcentage_b=pct_b,
        nombre_changements=possession.nombre_changements,
        nombre_sequences_a=possession.nombre_sequences_a,
        nombre_sequences_b=possession.nombre_sequences_b,
        collecteur_id=possession.collecteur_id,
        valide_par_id=possession.valide_par_id,
        officialisee_at=_as_utc(possession.officialisee_at) if possession.officialisee_at else None,
        derniere_transition_at=_as_utc(possession.derniere_transition_at)
        if possession.derniere_transition_at
        else None,
        intervalle_ouvert_depuis=ouvert_depuis,
        eligible_public=possession.eligible_public,
        motif_exclusion_public=possession.motif_exclusion_public,
        est_disponible=disponible,
        message=message,
        intervalles=intervals_out,
    )


async def snapshot_public_possession(
    db: AsyncSession, match: Match, possession: PossessionMatch | None
) -> PossessionPublicOut:
    """Filtre strictement la possession avant toute exposition publique."""
    equipe_a_nom, equipe_b_nom = await _noms_equipes(db, match)
    if (
        possession is None
        or _match_status(match) != StatutMatch.VALIDE.value
        or _value(possession.statut) != StatutPossession.OFFICIELLE.value
        or not possession.eligible_public
    ):
        return PossessionPublicOut(
            match_id=match.id,
            disponible=False,
            message="Possession non disponible",
            equipe_a_id=match.equipe_domicile_id,
            equipe_b_id=match.equipe_exterieur_id,
            equipe_a_nom=equipe_a_nom,
            equipe_b_nom=equipe_b_nom,
            statut=_value(possession.statut) if possession else None,
        )
    detail = await snapshot_possession(db, match, possession, include_intervals=False)
    if detail.temps_mesure_ms <= 0 or detail.pourcentage_a is None:
        return PossessionPublicOut(
            match_id=match.id,
            disponible=False,
            message="Possession non disponible",
            equipe_a_id=possession.equipe_a_id,
            equipe_b_id=possession.equipe_b_id,
            equipe_a_nom=equipe_a_nom,
            equipe_b_nom=equipe_b_nom,
            statut=StatutPossession.OFFICIELLE,
        )
    return PossessionPublicOut(
        match_id=match.id,
        disponible=True,
        message="Possession officielle",
        equipe_a_id=possession.equipe_a_id,
        equipe_b_id=possession.equipe_b_id,
        equipe_a_nom=equipe_a_nom,
        equipe_b_nom=equipe_b_nom,
        statut=StatutPossession.OFFICIELLE,
        temps_a=detail.temps_a,
        temps_b=detail.temps_b,
        temps_non_attribue=detail.temps_non_attribue,
        temps_a_ms=detail.temps_a_ms,
        temps_b_ms=detail.temps_b_ms,
        temps_mesure_ms=detail.temps_mesure_ms,
        pourcentage_a=detail.pourcentage_a,
        pourcentage_b=detail.pourcentage_b,
    )
