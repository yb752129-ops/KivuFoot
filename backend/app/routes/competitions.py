from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete as sql_delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.rbac import require_roles, verifier_organisateur_de_competition
from app.database import get_db
from app.models.club import Club
from app.models.evenement import EvenementMatch
from app.models.competition import Competition, OrganisateurCompetition, Saison, SaisonClub
from app.models.enums import ActionAudit, RoleUtilisateur
from app.models.match import Match, MatchParticipation
from app.models.stats import StatistiqueJoueur
from app.models.user import User
from app.schemas.competition import (
    ClubOut,
    CompetitionCreate,
    CompetitionOut,
    SaisonClubCreate,
    SaisonClubGroupeUpdate,
    SaisonClubOut,
    SaisonCreate,
    SaisonOut,
)
from app.services.audit import log_audit

router = APIRouter(tags=["Compétitions"])


def _saison_club_out(lien: SaisonClub, club: Club) -> SaisonClubOut:
    return SaisonClubOut(
        id=club.id,
        nom=club.nom,
        stade=club.stade,
        ville=club.ville,
        logo_url=club.logo_url,
        coach_nom=None,
        saison_id=lien.saison_id,
        club_id=lien.club_id,
        groupe=lien.groupe,
    )


@router.get("/competitions", response_model=list[CompetitionOut])
async def lister_competitions(db: AsyncSession = Depends(get_db)):
    # Les compétitions de démonstration ne sont plus jamais listées
    # (l'ancien paramètre inclure_demo a été supprimé avec l'environnement démo).
    query = select(Competition).where(Competition.est_demo.is_(False))
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/competitions/{competition_id}", response_model=CompetitionOut)
async def detail_competition(competition_id: int, db: AsyncSession = Depends(get_db)):
    comp = await db.get(Competition, competition_id)
    if comp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compétition introuvable.")
    return comp


@router.post("/competitions", response_model=CompetitionOut, status_code=status.HTTP_201_CREATED)
async def creer_competition(
    payload: CompetitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    # Règle §16 : aucune hypothèse figée sur la compétition pilote - elle
    # se crée entièrement via cette route, sans modification de code.
    comp = Competition(**payload.model_dump())
    db.add(comp)
    await db.flush()
    if current_user.role == RoleUtilisateur.ORGANISATEUR:
        db.add(OrganisateurCompetition(user_id=current_user.id, competition_id=comp.id))
    await log_audit(db, "competitions", comp.id, ActionAudit.INSERT, current_user.id, None, payload.model_dump(mode="json"))
    await db.commit()
    await db.refresh(comp)
    return comp


@router.delete("/competitions/{competition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def supprimer_competition(
    competition_id: int,
    purger: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN)),
):
    """Admin seulement. `purger=true` supprime aussi les données liées. Les clubs restent."""
    comp = await db.get(Competition, competition_id)
    if comp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compétition introuvable.")
    saison_ids = list(
        (await db.execute(select(Saison.id).where(Saison.competition_id == competition_id))).scalars().all()
    )
    if saison_ids and not purger:
        joue = await db.execute(select(Match.id).where(Match.saison_id.in_(saison_ids)).limit(1))
        if joue.scalar_one_or_none() is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Cette compétition a des matchs. Suppression bloquée.",
            )
    await log_audit(
        db,
        "competitions",
        comp.id,
        ActionAudit.DELETE,
        current_user.id,
        {"nom": comp.nom, "est_demo": comp.est_demo, "purger": purger, "saison_ids": saison_ids},
        None,
    )
    try:
        await db.execute(
            sql_delete(OrganisateurCompetition).where(OrganisateurCompetition.competition_id == competition_id)
        )
        await db.execute(sql_delete(StatistiqueJoueur).where(StatistiqueJoueur.competition_id == competition_id))
        if saison_ids and purger:
            match_ids = list(
                (await db.execute(select(Match.id).where(Match.saison_id.in_(saison_ids)))).scalars().all()
            )
            if match_ids:
                await db.execute(sql_delete(EvenementMatch).where(EvenementMatch.match_id.in_(match_ids)))
                await db.execute(sql_delete(MatchParticipation).where(MatchParticipation.match_id.in_(match_ids)))
                await db.execute(sql_delete(Match).where(Match.id.in_(match_ids)))
        if saison_ids:
            await db.execute(sql_delete(SaisonClub).where(SaisonClub.saison_id.in_(saison_ids)))
            await db.execute(sql_delete(Saison).where(Saison.competition_id == competition_id))
        await db.execute(sql_delete(Competition).where(Competition.id == competition_id))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Cette compétition a des matchs. Suppression bloquée.",
        )
    return None


@router.post("/saisons", response_model=SaisonOut, status_code=status.HTTP_201_CREATED)
async def creer_saison(
    payload: SaisonCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    comp = await db.get(Competition, payload.competition_id)
    if comp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compétition introuvable.")
    await verifier_organisateur_de_competition(payload.competition_id, current_user, db)
    saison = Saison(
        competition_id=payload.competition_id,
        nom=payload.nom,
        date_debut=payload.date_debut,
        date_fin=payload.date_fin,
    )
    db.add(saison)
    await db.flush()
    for club_id in payload.club_ids:
        db.add(SaisonClub(saison_id=saison.id, club_id=club_id))
    await log_audit(db, "saisons", saison.id, ActionAudit.INSERT, current_user.id, None, {"competition_id": payload.competition_id})
    await db.commit()
    await db.refresh(saison)
    return saison


@router.get("/saisons", response_model=list[SaisonOut])
async def lister_saisons(competition_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Saison).where(Saison.competition_id == competition_id))
    return result.scalars().all()


@router.get("/saisons/{saison_id}/clubs", response_model=list[SaisonClubOut])
async def lister_clubs_saison(saison_id: int, db: AsyncSession = Depends(get_db)):
    saison = await db.get(Saison, saison_id)
    if saison is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saison introuvable.")
    result = await db.execute(
        select(SaisonClub, Club)
        .join(Club, SaisonClub.club_id == Club.id)
        .where(SaisonClub.saison_id == saison_id)
        .order_by(Club.nom, Club.id)
    )
    return [_saison_club_out(lien, club) for lien, club in result.all()]


@router.post("/saisons/{saison_id}/clubs", response_model=SaisonClubOut, status_code=status.HTTP_201_CREATED)
async def inscrire_club_saison(
    saison_id: int,
    payload: SaisonClubCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    saison = await db.get(Saison, saison_id)
    if saison is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saison introuvable.")
    await verifier_organisateur_de_competition(saison.competition_id, current_user, db)
    club = await db.get(Club, payload.club_id)
    if club is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Équipe introuvable.")
    deja = await db.execute(
        select(SaisonClub).where(SaisonClub.saison_id == saison_id, SaisonClub.club_id == payload.club_id)
    )
    if deja.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cette équipe est déjà inscrite à cette saison.")
    lien = SaisonClub(saison_id=saison_id, club_id=payload.club_id, groupe=payload.groupe)
    db.add(lien)
    await log_audit(
        db,
        "saison_clubs",
        saison_id,
        ActionAudit.INSERT,
        current_user.id,
        None,
        {
            "saison_id": saison_id,
            "club_id": payload.club_id,
            "groupe": getattr(payload.groupe, "value", payload.groupe),
        },
    )
    await db.commit()
    await db.refresh(lien)
    await db.refresh(club)
    return _saison_club_out(lien, club)


@router.patch("/saisons/{saison_id}/clubs/{club_id}", response_model=SaisonClubOut)
async def modifier_groupe_club_saison(
    saison_id: int,
    club_id: int,
    payload: SaisonClubGroupeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    saison = await db.get(Saison, saison_id)
    if saison is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saison introuvable.")
    await verifier_organisateur_de_competition(saison.competition_id, current_user, db)
    result = await db.execute(
        select(SaisonClub, Club)
        .join(Club, SaisonClub.club_id == Club.id)
        .where(SaisonClub.saison_id == saison_id, SaisonClub.club_id == club_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Équipe non inscrite.")
    lien, club = row
    ancien = getattr(lien.groupe, "value", lien.groupe)
    nouveau = getattr(payload.groupe, "value", payload.groupe)
    if ancien == nouveau:
        return _saison_club_out(lien, club)

    # Changer une affectation après programmation rendrait les matchs de
    # poule historiques incohérents. On bloque sans supprimer ni réécrire.
    from sqlalchemy import or_

    match_existant = await db.execute(
        select(Match.id)
        .where(
            Match.saison_id == saison_id,
            Match.phase == "poule",
            or_(Match.equipe_domicile_id == club_id, Match.equipe_exterieur_id == club_id),
        )
        .limit(1)
    )
    if match_existant.scalar_one_or_none() is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Groupe non modifiable : cette équipe a déjà un match de poule.",
        )

    lien.groupe = payload.groupe
    await log_audit(
        db,
        "saison_clubs",
        saison_id,
        ActionAudit.UPDATE,
        current_user.id,
        {"saison_id": saison_id, "club_id": club_id, "groupe": ancien},
        {"saison_id": saison_id, "club_id": club_id, "groupe": nouveau},
    )
    await db.commit()
    await db.refresh(lien)
    await db.refresh(club)
    return _saison_club_out(lien, club)


@router.delete("/saisons/{saison_id}/clubs/{club_id}", status_code=status.HTTP_204_NO_CONTENT)
async def desinscrire_club_saison(
    saison_id: int,
    club_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    saison = await db.get(Saison, saison_id)
    if saison is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saison introuvable.")
    await verifier_organisateur_de_competition(saison.competition_id, current_user, db)
    from sqlalchemy import or_
    from app.models.match import Match

    joue = await db.execute(
        select(Match.id).where(
            Match.saison_id == saison_id,
            or_(Match.equipe_domicile_id == club_id, Match.equipe_exterieur_id == club_id),
        ).limit(1)
    )
    if joue.scalar_one_or_none() is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Cette équipe a des matchs dans cette saison. Désinscription bloquée.",
        )
    lien = await db.execute(
        select(SaisonClub).where(SaisonClub.saison_id == saison_id, SaisonClub.club_id == club_id)
    )
    row = lien.scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Équipe non inscrite.")
    await db.delete(row)
    await log_audit(
        db, "saison_clubs", saison_id, ActionAudit.DELETE, current_user.id,
        {"club_id": club_id}, None,
    )
    await db.commit()
    return None
