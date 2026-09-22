from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.club import Club
from app.models.competition import Competition, Saison, SaisonClub
from app.models.effectif import EffectifClub
from app.models.enums import ActionAudit, StatutEffectif, StatutJoueur
from app.models.joueur import Joueur
from app.services.audit import log_audit


async def ligne_effectif(
    db: AsyncSession, saison_id: int, club_id: int
) -> EffectifClub | None:
    result = await db.execute(
        select(EffectifClub).where(
            EffectifClub.saison_id == saison_id,
            EffectifClub.club_id == club_id,
        )
    )
    return result.scalar_one_or_none()


async def compte_joueurs(
    db: AsyncSession, club_id: int
) -> tuple[int, int]:
    """Retourne (joueurs actifs, joueurs sans photo validée)."""
    base = (
        Joueur.club_actuel_id == club_id,
        Joueur.fusionne.is_(False),
        Joueur.anonymise.is_(False),
        Joueur.statut == StatutJoueur.ACTIF,
    )
    total = await db.scalar(select(func.count(Joueur.id)).where(*base))
    sans_photo = await db.scalar(
        select(func.count(Joueur.id)).where(*base, Joueur.photo_actuelle_id.is_(None))
    )
    return int(total or 0), int(sans_photo or 0)


def statut_visible(ligne: EffectifClub | None, total_joueurs: int) -> StatutEffectif:
    if ligne is None:
        return StatutEffectif.EN_COURS if total_joueurs else StatutEffectif.A_COMPLETER
    statut = ligne.statut
    if statut == StatutEffectif.A_COMPLETER and total_joueurs:
        return StatutEffectif.EN_COURS
    return statut


def peut_soumettre(statut: StatutEffectif, total_joueurs: int) -> bool:
    return total_joueurs > 0 and statut in {
        StatutEffectif.EN_COURS,
        StatutEffectif.A_CORRIGER,
    }


async def resume_effectif(
    db: AsyncSession,
    saison_id: int,
    club: Club,
    ligne: EffectifClub | None = None,
) -> dict:
    if ligne is None:
        ligne = await ligne_effectif(db, saison_id, club.id)
    total, sans_photo = await compte_joueurs(db, club.id)
    statut = statut_visible(ligne, total)
    return {
        "saison_id": saison_id,
        "club_id": club.id,
        "club_nom": club.nom,
        "statut": statut,
        "total_joueurs": total,
        "joueurs_sans_photo": sans_photo,
        "soumis_at": ligne.soumis_at if ligne else None,
        "soumis_par_id": ligne.soumis_par_id if ligne else None,
        "traite_at": ligne.traite_at if ligne else None,
        "traite_par_id": ligne.traite_par_id if ligne else None,
        "motif_retour": ligne.motif_retour if ligne else None,
        "peut_soumettre": peut_soumettre(statut, total),
    }


async def marquer_effectif_modifie(
    db: AsyncSession, club_id: int, actor_id: int | None
) -> None:
    """Une nouvelle fiche joueur invalide la dernière soumission du club."""
    result = await db.execute(
        select(EffectifClub)
        .join(Saison, Saison.id == EffectifClub.saison_id)
        .join(Competition, Competition.id == Saison.competition_id)
        .where(
            EffectifClub.club_id == club_id,
            Competition.est_active.is_(True),
            EffectifClub.statut.in_(
                [
                    StatutEffectif.SOUMIS,
                    StatutEffectif.VALIDE,
                    StatutEffectif.A_CORRIGER,
                ]
            ),
        )
    )
    for ligne in result.scalars().all():
        ancien = getattr(ligne.statut, "value", ligne.statut)
        ligne.statut = StatutEffectif.EN_COURS
        ligne.motif_retour = "Effectif modifié : une nouvelle soumission est requise."
        await log_audit(
            db,
            "effectifs_clubs",
            ligne.id,
            ActionAudit.UPDATE,
            actor_id,
            {"statut": ancien},
            {"statut": StatutEffectif.EN_COURS.value, "motif": ligne.motif_retour},
        )
