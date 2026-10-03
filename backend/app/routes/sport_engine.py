from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import require_roles, verifier_organisateur_de_competition, verifier_organisateur_du_match
from app.database import get_db
from app.models.competition import Saison
from app.models.enums import ActionAudit, RoleUtilisateur, StatutMatch, StatutValidationEvenement, TypeEvenement
from app.models.evenement import EvenementMatch
from app.models.match import Match
from app.models.sport_engine import AnomalieHistorique, DecisionSportive, SanctionDisciplinaire
from app.models.user import User
from app.schemas.sport_engine import (
    AnomalieOut,
    AnomalieUpdate,
    DecisionSportiveCreate,
    DecisionSportiveOut,
    DisciplineOut,
)
from app.services.anomalies_historiques import scan_saison
from app.services.audit import log_audit
from app.services.discipline import get_discipline_summary, persist_calculated_sanctions
from app.services.reglements import get_reglement_pour_match

router = APIRouter(tags=["Moteur sportif"])


def _value(value):
    return value.value if hasattr(value, "value") else value


@router.get("/discipline/joueurs/{joueur_id}", response_model=DisciplineOut)
async def discipline_joueur(
    joueur_id: int,
    saison_id: int,
    match_id: int,
    db: AsyncSession = Depends(get_db),
):
    match = await db.get(Match, match_id)
    if match is None or match.saison_id != saison_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match ou saison introuvable.")
    reglement = await get_reglement_pour_match(db, match, allow_active_for_new=True)
    return await get_discipline_summary(db, joueur_id, match, reglement)


@router.get("/discipline/matchs/{match_id}", response_model=list[DisciplineOut])
async def discipline_match(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR, RoleUtilisateur.CLUB_MANAGER, RoleUtilisateur.COACH)
    ),
):
    match = await db.get(Match, match_id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    if current_user.role in (RoleUtilisateur.ORGANISATEUR, RoleUtilisateur.ADMIN):
        await verifier_organisateur_du_match(match_id, current_user, db)
    elif current_user.club_id not in (match.equipe_domicile_id, match.equipe_exterieur_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Vous ne gérez pas une équipe de ce match.")
    event_rows = (
        await db.execute(
            select(EvenementMatch.joueur_id)
            .where(
                EvenementMatch.match_id == match_id,
                EvenementMatch.joueur_id.is_not(None),
                EvenementMatch.type.in_([TypeEvenement.CARTON_JAUNE, TypeEvenement.CARTON_ROUGE]),
                EvenementMatch.statut_validation == StatutValidationEvenement.VALIDE,
                EvenementMatch.refuse.is_(False),
            )
            .distinct()
        )
    ).scalars().all()
    reglement = await get_reglement_pour_match(db, match, allow_active_for_new=True)
    return [await get_discipline_summary(db, joueur_id, match, reglement) for joueur_id in event_rows]


@router.post("/discipline/saisons/{saison_id}/recalculer")
async def recalculer_discipline(
    saison_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    saison = await db.get(Saison, saison_id)
    if saison is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saison introuvable.")
    await verifier_organisateur_de_competition(saison.competition_id, current_user, db)
    matches = (
        await db.execute(
            select(Match)
            .where(Match.saison_id == saison_id, Match.statut == StatutMatch.PROGRAMME)
            .order_by(Match.date_heure, Match.id)
        )
    ).scalars().all()
    joueurs = (
        await db.execute(
            select(EvenementMatch.joueur_id)
            .join(Match, Match.id == EvenementMatch.match_id)
            .where(
                Match.saison_id == saison_id,
                Match.statut == StatutMatch.VALIDE,
                EvenementMatch.joueur_id.is_not(None),
                EvenementMatch.type.in_([TypeEvenement.CARTON_JAUNE, TypeEvenement.CARTON_ROUGE]),
                EvenementMatch.statut_validation == StatutValidationEvenement.VALIDE,
                EvenementMatch.refuse.is_(False),
            )
            .distinct()
        )
    ).scalars().all()
    created = []
    for match in matches:
        reglement = await get_reglement_pour_match(db, match, allow_active_for_new=True)
        if reglement is None:
            continue
        for joueur_id in joueurs:
            created.extend(await persist_calculated_sanctions(db, joueur_id, match, reglement))
    await db.commit()
    return {"saison_id": saison_id, "sanctions_creees": len(created), "mode": "calcul_non_destructif"}


@router.post("/discipline/sanctions/{sanction_id}/decision", response_model=DecisionSportiveOut)
async def decider_sanction(
    sanction_id: int,
    payload: DecisionSportiveCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    sanction = await db.get(SanctionDisciplinaire, sanction_id)
    if sanction is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sanction introuvable.")
    await verifier_organisateur_de_competition(sanction.competition_id, current_user, db)
    details = payload.details or {}
    ancien_statut = sanction.statut
    ancien_restants = sanction.matchs_restants
    match_id = details.get("match_id") if payload.action == "autoriser_participation" else None
    if payload.action == "autoriser_participation" and not isinstance(match_id, int):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Une autorisation exceptionnelle doit préciser le match concerné.",
        )
    if payload.action == "confirmer":
        sanction.statut = "confirmee"
    elif payload.action == "modifier":
        sanction.statut = "modifiee"
        if isinstance(details.get("matchs_restants"), int) and details["matchs_restants"] >= 0:
            sanction.matchs_restants = details["matchs_restants"]
        if isinstance(details.get("nombre_matchs"), int) and details["nombre_matchs"] >= 0:
            sanction.nombre_matchs = details["nombre_matchs"]
    elif payload.action == "annuler":
        sanction.statut = "annulee"
        sanction.matchs_restants = 0
    elif payload.action == "prolonger":
        ajout = details.get("ajout_matchs")
        if not isinstance(ajout, int) or ajout < 1:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Une prolongation doit préciser un nombre de matchs positif.",
            )
        sanction.statut = "confirmee"
        sanction.nombre_matchs += ajout
        sanction.matchs_restants += ajout
    elif payload.action == "autoriser_participation":
        # La décision autorise ce match sans supprimer ni modifier la
        # sanction source, conformément à la politique mixte.
        sanction.statut = ancien_statut

    decision = DecisionSportive(
        competition_id=sanction.competition_id,
        saison_id=sanction.saison_id,
        match_id=match_id,
        joueur_id=sanction.joueur_id,
        sanction_id=sanction.id,
        type_decision="eligibilite" if payload.action == "autoriser_participation" else "discipline",
        action=payload.action,
        statut="confirmee",
        motif=payload.motif,
        details=details,
        decide_par_id=current_user.id,
    )
    db.add(decision)
    await db.flush()
    await log_audit(
        db,
        "sanctions_disciplinaires",
        sanction.id,
        ActionAudit.UPDATE,
        current_user.id,
        {"statut": ancien_statut, "matchs_restants": ancien_restants},
        {"statut": sanction.statut, "matchs_restants": sanction.matchs_restants, "decision_id": decision.id, "action": payload.action},
    )
    await db.commit()
    await db.refresh(decision)
    return decision


@router.get("/anomalies-historiques", response_model=list[AnomalieOut])
async def anomalies_historiques(
    saison_id: int,
    statut_anomalie: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    saison = await db.get(Saison, saison_id)
    if saison is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saison introuvable.")
    await verifier_organisateur_de_competition(saison.competition_id, current_user, db)
    query = select(AnomalieHistorique).where(AnomalieHistorique.saison_id == saison_id).order_by(AnomalieHistorique.id)
    if statut_anomalie:
        query = query.where(AnomalieHistorique.statut == statut_anomalie)
    return list((await db.execute(query)).scalars().all())


@router.post("/anomalies-historiques/scan", response_model=list[AnomalieOut])
async def scanner_anomalies(
    saison_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    saison = await db.get(Saison, saison_id)
    if saison is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saison introuvable.")
    await verifier_organisateur_de_competition(saison.competition_id, current_user, db)
    rows = await scan_saison(db, saison_id, current_user.id)
    await db.commit()
    return rows


@router.patch("/anomalies-historiques/{anomalie_id}", response_model=AnomalieOut)
async def traiter_anomalie(
    anomalie_id: int,
    payload: AnomalieUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    row = await db.get(AnomalieHistorique, anomalie_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Anomalie introuvable.")
    saison = await db.get(Saison, row.saison_id)
    if saison is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saison introuvable.")
    await verifier_organisateur_de_competition(saison.competition_id, current_user, db)
    ancien = {"statut": row.statut, "decision": row.decision}
    row.statut = payload.statut
    row.decision = payload.decision
    row.decide_par_id = current_user.id
    row.decide_at = datetime.now(timezone.utc)
    await log_audit(db, "anomalies_historiques", row.id, ActionAudit.UPDATE, current_user.id, ancien, {"statut": row.statut, "decision": row.decision})
    await db.commit()
    await db.refresh(row)
    return row
