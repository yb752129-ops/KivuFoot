"""Records recalculables à partir des seules données officielles."""
from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import StatutMatch, StatutValidationEvenement, TypeEvenement
from app.models.evenement import EvenementMatch
from app.models.joueur import Joueur
from app.models.match import Match


def _value(value):
    return value.value if hasattr(value, "value") else value


async def calculer_records(db: AsyncSession, saison_id: int) -> list[dict]:
    matchs = (
        await db.execute(select(Match).where(Match.saison_id == saison_id, Match.statut == StatutMatch.VALIDE))
    ).scalars().all()
    events = (
        await db.execute(
            select(EvenementMatch)
            .join(Match, Match.id == EvenementMatch.match_id)
            .where(
                Match.saison_id == saison_id,
                Match.statut == StatutMatch.VALIDE,
                EvenementMatch.statut_validation == StatutValidationEvenement.VALIDE,
                EvenementMatch.refuse.is_(False),
            )
        )
    ).scalars().all()
    records: list[dict] = []
    if matchs:
        plus_buts = max(matchs, key=lambda m: (m.score_domicile + m.score_exterieur, -m.id))
        plus_large = max(matchs, key=lambda m: (abs(m.score_domicile - m.score_exterieur), -m.id))
        records.extend([
            {
                "code": "plus_buts_match",
                "valeur": plus_buts.score_domicile + plus_buts.score_exterieur,
                "match_id": plus_buts.id,
                "message": f"{plus_buts.score_domicile + plus_buts.score_exterieur} but(s) dans le match #{plus_buts.id}.",
                "source": "matchs_valides",
            },
            {
                "code": "plus_large_victoire",
                "valeur": abs(plus_large.score_domicile - plus_large.score_exterieur),
                "match_id": plus_large.id,
                "message": f"Écart de {abs(plus_large.score_domicile - plus_large.score_exterieur)} dans le match #{plus_large.id}.",
                "source": "matchs_valides",
            },
        ])
    cards = Counter(_value(event.type) for event in events if _value(event.type) in ("carton_jaune", "carton_rouge"))
    if cards:
        record_match = max(matchs, key=lambda m: sum(1 for event in events if event.match_id == m.id and _value(event.type) in ("carton_jaune", "carton_rouge")), default=None)
        if record_match:
            total = sum(1 for event in events if event.match_id == record_match.id and _value(event.type) in ("carton_jaune", "carton_rouge"))
            records.append({"code": "plus_cartons_match", "valeur": total, "match_id": record_match.id, "message": f"{total} carton(s) dans le match #{record_match.id}.", "source": "evenements_valides"})
    # Le meilleur buteur public est reconstruit depuis les mêmes événements
    # officiels que le reste de cette route. Un agrégat historique isolé ne
    # doit pas pouvoir laisser fuiter un événement refuse.
    buts_par_joueur = Counter()
    per_player_match = defaultdict(Counter)
    for event in events:
        event_type = _value(event.type)
        penalty_marque = event_type == "penalty" and _value(event.resultat) == "marque"
        if event.joueur_id and (event_type == "but" or penalty_marque):
            buts_par_joueur[event.joueur_id] += 1
            per_player_match[(event.match_id, event.joueur_id)][event_type] += 1
    if buts_par_joueur:
        joueur_id, total_buts = max(buts_par_joueur.items(), key=lambda item: (item[1], -item[0]))
        joueur = await db.get(Joueur, joueur_id)
        records.append({
            "code": "meilleur_buteur_edition",
            "valeur": total_buts,
            "joueur_id": joueur_id,
            "message": f"{joueur.nom_complet if joueur else 'Joueur'} : {total_buts} but(s).",
            "source": "evenements_valides",
        })
    if per_player_match:
        (match_id, joueur_id), count = max(per_player_match.items(), key=lambda item: sum(item[1].values()))
        joueur = await db.get(Joueur, joueur_id)
        records.append({"code": "plus_buts_joueur_match", "valeur": sum(count.values()), "match_id": match_id, "joueur_id": joueur_id, "message": f"{joueur.nom_complet if joueur else 'Joueur'} : {sum(count.values())} but(s) dans le match #{match_id}.", "source": "evenements_valides"})
    return records
