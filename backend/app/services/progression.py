"""Progression et qualification dérivées des matchs officiellement validés."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.club import Club
from app.models.competition import Saison, SaisonClub
from app.models.enums import StatutMatch
from app.models.match import Match
from app.services.calcul_classement import LigneClassement, calculer_classement
from app.services.reglements import get_reglement_actif


def _value(value):
    return value.value if hasattr(value, "value") else value


def _rank_key(row: LigneClassement, criteres: list[str] | None = None) -> tuple:
    values = {
        "points": row.points,
        "difference_buts": row.difference_buts,
        "buts_marques": row.buts_marques,
        "buts_encaisses": row.buts_encaisses,
        "victoires": row.victoires,
        "nuls": row.nuls,
        "defaites": row.defaites,
        "matchs_joues": row.matchs_joues,
    }
    selected = criteres or ["points", "difference_buts", "buts_marques"]
    numeric = [-values[name] for name in selected if name in values]
    return (*numeric, row.club_nom, row.club_id)


async def progression_saison(db: AsyncSession, saison_id: int) -> dict:
    saison = await db.get(Saison, saison_id)
    if saison is None:
        return {"saison_id": saison_id, "statut": "introuvable", "lignes": []}

    inscriptions = (
        await db.execute(
            select(SaisonClub, Club)
            .join(Club, Club.id == SaisonClub.club_id)
            .where(SaisonClub.saison_id == saison_id)
            .order_by(Club.nom, Club.id)
        )
    ).all()
    general = {row.club_id: row for row in await calculer_classement(db, saison_id)}
    matches = (
        await db.execute(
            select(Match).where(
                Match.saison_id == saison_id,
                Match.statut.in_([StatutMatch.VALIDE, StatutMatch.PROGRAMME, StatutMatch.EN_COURS, StatutMatch.TERMINE]),
            )
        )
    ).scalars().all()
    reglement = await get_reglement_actif(db, saison_id)
    configuration = reglement.configuration if reglement else {}
    qualification = (configuration.get("qualification") or {}) if isinstance(configuration, dict) else {}
    qualifies_par_groupe = qualification.get("qualifies_par_groupe") if isinstance(qualification, dict) else None
    meilleurs_suivants = qualification.get("meilleurs_suivants", 0) if isinstance(qualification, dict) else 0
    calendrier_complet = bool(qualification.get("calendrier_complet", False)) if isinstance(qualification, dict) else False
    qualification_criteres = qualification.get("criteres_departage") if isinstance(qualification, dict) else None
    if not isinstance(qualification_criteres, list) or not qualification_criteres:
        qualification_criteres = None

    # Les rangs sont calculés avec le classement officiel existant. Aucun
    # groupe n'est déduit de Match.groupe : SaisonClub reste la source.
    rangs_par_groupe: dict[str, dict[int, int]] = {}
    candidats_suivants: list[LigneClassement] = []
    if qualifies_par_groupe is not None:
        groupes = sorted({link.groupe for link, _ in inscriptions if link.groupe})
        for groupe in groupes:
            lignes_groupe = await calculer_classement(db, saison_id, groupe=groupe)
            rangs_par_groupe[groupe] = {ligne.club_id: index for index, ligne in enumerate(lignes_groupe, start=1)}
            candidats_suivants.extend(lignes_groupe[int(qualifies_par_groupe):])

    qualified_ids: set[int] = set()
    if qualifies_par_groupe is not None and calendrier_complet:
        for ranks in rangs_par_groupe.values():
            qualified_ids.update(club_id for club_id, rank in ranks.items() if rank <= qualifies_par_groupe)
        if meilleurs_suivants:
            candidats_suivants.sort(key=lambda row: _rank_key(row, qualification_criteres))
            qualified_ids.update(row.club_id for row in candidats_suivants[: int(meilleurs_suivants)])

    lignes = []
    for link, club in inscriptions:
        played = [m for m in matches if club.id in (m.equipe_domicile_id, m.equipe_exterieur_id)]
        done = [m for m in played if _value(m.statut) == StatutMatch.VALIDE.value]
        not_official = [m for m in played if _value(m.statut) != StatutMatch.VALIDE.value]
        row = general.get(club.id)
        status = "indetermine"
        explanation = "Règlement de qualification non configuré pour cette édition."
        group = _value(link.groupe)
        rank = rangs_par_groupe.get(group, {}).get(club.id) if group else None

        if qualifies_par_groupe is not None:
            if not group or rank is None:
                explanation = "Aucun groupe officiel exploitable pour calculer la qualification."
            elif not calendrier_complet or not played or not_official:
                status = "en_course"
                explanation = (
                    "Les résultats ne permettent pas encore d'arrêter une qualification officielle. "
                    "Le calendrier complet et les matchs validés sont requis."
                )
            elif club.id in qualified_ids:
                status = "qualifie"
                explanation = f"Rang {rank} du groupe {group}, selon le règlement actif."
            else:
                status = "non_qualifie"
                explanation = f"Rang {rank} du groupe {group}, selon le règlement actif."

        lignes.append(
            {
                "club_id": club.id,
                "club_nom": club.nom,
                "groupe": group,
                "matchs_joues": row.matchs_joues if row else 0,
                "matchs_restants": len(not_official),
                "points": row.points if row else 0,
                "difference_buts": row.difference_buts if row else 0,
                "buts_marques": row.buts_marques if row else 0,
                "rang_groupe": rank,
                "statut_qualification": status,
                "explication": explanation,
                "source": "matchs_valides_et_reglement_versionne",
            }
        )
    return {
        "saison_id": saison_id,
        "reglement_version_id": reglement.id if reglement else None,
        "statut": "calcule" if reglement else "reglement_absent",
        "qualification_arretee": bool(qualified_ids),
        "lignes": lignes,
    }
