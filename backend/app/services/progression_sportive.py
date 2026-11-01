"""Qualification sportive des phases à élimination directe.

Les décisions sont dérivées exclusivement des matchs officiellement validés.
Le statut administratif de ``saison_clubs`` n'est jamais écrit ici. Les
appariements ne sont jamais devinés : un match cible doit explicitement
référencer le match dont son emplacement reçoit le vainqueur.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException, status

from app.models.enums import ActionAudit, StatutMatch
from app.models.match import Match
from app.models.sport_engine import MatchQualificationSlot
from app.services.audit import log_audit
from app.services.tirs_au_but import PHASES_ELIMINATOIRES, vainqueur_tirs_au_but

ORDRE_PHASE = {"barrage": 1, "quart": 2, "demi": 3, "finale": 4}
PHASE_PRECEDENTE = {"quart": "barrage", "demi": "quart", "finale": "demi"}


def _value(value):
    return value.value if hasattr(value, "value") else value


def vainqueur_match_eliminatoire(match: Match) -> tuple[str, int] | None:
    """Retourne (côté, club_id), y compris si le score est départagé aux tirs."""
    if _value(match.phase) not in PHASES_ELIMINATOIRES:
        return None
    if match.equipe_domicile_id is None or match.equipe_exterieur_id is None:
        return None
    if match.score_domicile > match.score_exterieur:
        return "domicile", match.equipe_domicile_id
    if match.score_exterieur > match.score_domicile:
        return "exterieur", match.equipe_exterieur_id
    cote = vainqueur_tirs_au_but(match.tirs_au_but or [])
    if cote == "domicile":
        return cote, match.equipe_domicile_id
    if cote == "exterieur":
        return cote, match.equipe_exterieur_id
    return None


async def etats_sportifs_saison(db: AsyncSession, saison_id: int) -> dict[int, dict]:
    """Projection courante qualifié/éliminé, sans modifier les inscriptions."""
    rows = (
        await db.execute(
            select(Match).where(
                Match.saison_id == saison_id,
                Match.statut == StatutMatch.VALIDE.value,
                Match.phase.in_(PHASES_ELIMINATOIRES),
            )
        )
    ).scalars().all()
    rows.sort(key=lambda match: (ORDRE_PHASE.get(_value(match.phase), 0), match.date_heure, match.id))
    etats: dict[int, dict] = {}
    for match in rows:
        resultat = vainqueur_match_eliminatoire(match)
        if resultat is None:
            continue
        cote, gagnant = resultat
        perdant = match.equipe_exterieur_id if cote == "domicile" else match.equipe_domicile_id
        statut_gagnant = "champion" if _value(match.phase) == "finale" else "qualifie"
        etats[gagnant] = {
            "statut_sportif": statut_gagnant,
            "phase_sportive": _value(match.phase),
            "match_sportif_id": match.id,
        }
        etats[perdant] = {
            "statut_sportif": "elimine",
            "phase_sportive": _value(match.phase),
            "match_sportif_id": match.id,
        }
    return etats


async def verifier_equipe_directement_nommable(
    db: AsyncSession,
    saison_id: int,
    club_id: int,
    phase_cible: str,
) -> None:
    """Empêche de re-sélectionner un perdant comme qualifié au tour suivant.

    Si l'équipe a déjà disputé le tour immédiatement précédent, la suite doit
    référencer le match source. Cela permet au moteur de remplir le bon slot
    dès validation, sans déduire un appariement à partir des noms d'équipes.
    """
    phase_precedente = PHASE_PRECEDENTE.get(phase_cible)
    if phase_precedente is None:
        return
    matches_precedents = (
        await db.execute(
            select(Match).where(
                Match.saison_id == saison_id,
                Match.phase == phase_precedente,
                (Match.equipe_domicile_id == club_id) | (Match.equipe_exterieur_id == club_id),
                Match.statut != StatutMatch.ANNULE.value,
            )
        )
    ).scalars().all()
    if not matches_precedents:
        return  # équipe qualifiée directement depuis la phase précédente du tournoi

    etats = await etats_sportifs_saison(db, saison_id)
    etat = etats.get(club_id, {})
    if etat.get("statut_sportif") == "elimine":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cette équipe a été éliminée en phase {etat.get('phase_sportive')} et ne peut pas être sélectionnée en {phase_cible}.",
        )
    raise HTTPException(
        status.HTTP_409_CONFLICT,
        f"Cette équipe a joué la phase {phase_precedente} : sélectionnez le vainqueur de son match source pour la phase {phase_cible}.",
    )


async def verifier_source_qualification(
    db: AsyncSession,
    *,
    saison_id: int,
    phase_cible: str,
    match_source_id: int,
    cote_cible: str,
) -> tuple[Match, int | None]:
    """Valide la liaison et retourne le match source et son vainqueur éventuel."""
    phase_precedente = PHASE_PRECEDENTE.get(phase_cible)
    if cote_cible not in ("domicile", "exterieur") or phase_precedente is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Un vainqueur source n'est autorisé que pour le tour suivant.")
    source = await db.scalar(select(Match).where(Match.id == match_source_id).with_for_update())
    if source is None or source.saison_id != saison_id or _value(source.phase) != phase_precedente:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Le match source doit appartenir à cette saison et être un match de phase {phase_precedente}.",
        )
    if _value(source.statut) in (StatutMatch.ANNULE.value, StatutMatch.CONTESTE.value):
        raise HTTPException(status.HTTP_409_CONFLICT, "Un match annulé ou contesté ne peut pas qualifier une équipe.")
    if source.equipe_domicile_id is None or source.equipe_exterieur_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Le match source n'a pas encore ses deux équipes.")
    deja_utilise = await db.scalar(
        select(MatchQualificationSlot.id).where(MatchQualificationSlot.match_source_id == match_source_id)
    )
    if deja_utilise is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Le vainqueur de ce match source est déjà affecté à un emplacement.")
    winner_id = None
    if _value(source.statut) == StatutMatch.VALIDE.value:
        result = vainqueur_match_eliminatoire(source)
        if result is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Le résultat officiel du match source ne détermine aucun vainqueur.")
        _, winner_id = result
    return source, winner_id


async def propager_vainqueur_vers_tour_suivant(
    db: AsyncSession,
    match_source: Match,
    valide_par_id: int,
) -> None:
    """Remplit atomiquement les emplacements explicitement liés au match validé."""
    if _value(match_source.phase) not in PHASES_ELIMINATOIRES:
        return
    resultat = vainqueur_match_eliminatoire(match_source)
    if resultat is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Un match éliminatoire à égalité exige une séance de tirs au but décidée avant validation.",
        )
    _, winner_id = resultat
    slots = (
        await db.execute(
            select(MatchQualificationSlot)
            .where(MatchQualificationSlot.match_source_id == match_source.id)
            .order_by(MatchQualificationSlot.id)
        )
    ).scalars().all()
    for slot in slots:
        target = await db.scalar(
            select(Match).where(Match.id == slot.match_cible_id).with_for_update()
        )
        if target is None or target.saison_id != match_source.saison_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Le match cible de qualification n'est plus disponible.")
        if _value(target.phase) != {"barrage": "quart", "quart": "demi", "demi": "finale"}.get(_value(match_source.phase)):
            raise HTTPException(status.HTTP_409_CONFLICT, "La phase du match cible ne correspond plus à la progression.")
        if _value(target.statut) != StatutMatch.PROGRAMME.value or target.started_at or target.locked:
            raise HTTPException(status.HTTP_409_CONFLICT, "Le match cible a déjà commencé : la qualification ne peut pas remplacer son emplacement.")
        autre_cote_id = target.equipe_exterieur_id if slot.cote == "domicile" else target.equipe_domicile_id
        if autre_cote_id == winner_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Un même club ne peut pas occuper les deux côtés du match cible.")
        if slot.cote == "domicile":
            ancien_id = target.equipe_domicile_id
            if ancien_id not in (None, winner_id):
                raise HTTPException(status.HTTP_409_CONFLICT, "L'emplacement domicile du match cible est déjà occupé par une autre équipe.")
            target.equipe_domicile_id = winner_id
        else:
            ancien_id = target.equipe_exterieur_id
            if ancien_id not in (None, winner_id):
                raise HTTPException(status.HTTP_409_CONFLICT, "L'emplacement extérieur du match cible est déjà occupé par une autre équipe.")
            target.equipe_exterieur_id = winner_id
        if ancien_id != winner_id:
            await log_audit(
                db,
                "matchs",
                target.id,
                ActionAudit.UPDATE,
                valide_par_id,
                {f"equipe_{slot.cote}_id": ancien_id, "source_match_id": match_source.id},
                {f"equipe_{slot.cote}_id": winner_id, "qualification_automatique": True},
            )
    await db.flush()


async def retirer_vainqueur_des_matchs_cibles(
    db: AsyncSession,
    match_source: Match,
    modifie_par_id: int,
) -> None:
    """Révoque les slots encore vierges avant d'annuler un résultat source."""
    slots = (
        await db.execute(
            select(MatchQualificationSlot)
            .where(MatchQualificationSlot.match_source_id == match_source.id)
            .order_by(MatchQualificationSlot.id)
        )
    ).scalars().all()
    resultat = vainqueur_match_eliminatoire(match_source)
    vainqueur_id = resultat[1] if resultat is not None else None
    for slot in slots:
        target = await db.scalar(
            select(Match).where(Match.id == slot.match_cible_id).with_for_update()
        )
        if target is None:
            continue
        if _value(target.statut) != StatutMatch.PROGRAMME.value or target.started_at or target.locked:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Le résultat ne peut pas être annulé : le match du tour suivant a commencé ou a été verrouillé.",
            )
        field = f"equipe_{slot.cote}_id"
        ancien_id = getattr(target, field)
        if ancien_id is not None and ancien_id != vainqueur_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "L'emplacement de qualification a été modifié manuellement; révocation refusée.")
        if ancien_id == vainqueur_id and ancien_id is not None:
            setattr(target, field, None)
            await log_audit(
                db,
                "matchs",
                target.id,
                ActionAudit.UPDATE,
                modifie_par_id,
                {field: ancien_id, "source_match_id": match_source.id},
                {field: None, "qualification_revoquee": True},
            )
    await db.flush()
