"""
Calcul du classement d'une saison.

Règle §3.5 de la spécification :
- Calculé UNIQUEMENT à partir des matchs `statut = 'valide'` (jamais les
  matchs bruts/en_attente/contestés).
- Points : victoire = 3, nul = 1, défaite = 0.
- Tri : points desc, puis différence de buts desc, puis buts marqués desc.
- Forfait : le score 3-0 est appliqué et compté normalement dans le
  classement, mais le match reste marqué `forfait=True` pour la
  traçabilité (affichage public distinct, voir routes/matchs.py).
"""
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.club import Club
from app.models.enums import StatutMatch
from app.models.match import Match


class LigneClassement:
    def __init__(self, club_id: int, club_nom: str):
        self.club_id = club_id
        self.club_nom = club_nom
        self.matchs_joues = 0
        self.victoires = 0
        self.nuls = 0
        self.defaites = 0
        self.buts_marques = 0
        self.buts_encaisses = 0

    @property
    def difference_buts(self) -> int:
        return self.buts_marques - self.buts_encaisses

    @property
    def points(self) -> int:
        return self.victoires * 3 + self.nuls


async def calculer_classement(db: AsyncSession, saison_id: int) -> list[LigneClassement]:
    result = await db.execute(
        select(Match).where(Match.saison_id == saison_id, Match.statut == StatutMatch.VALIDE)
    )
    matchs_valides = result.scalars().all()

    club_ids: set[int] = set()
    for m in matchs_valides:
        if m.equipe_domicile_id:
            club_ids.add(m.equipe_domicile_id)
        if m.equipe_exterieur_id:
            club_ids.add(m.equipe_exterieur_id)

    if not club_ids:
        return []

    clubs_result = await db.execute(select(Club).where(Club.id.in_(club_ids)))
    clubs_par_id = {c.id: c for c in clubs_result.scalars().all()}

    lignes: dict[int, LigneClassement] = {
        cid: LigneClassement(cid, clubs_par_id[cid].nom) for cid in club_ids if cid in clubs_par_id
    }

    for m in matchs_valides:
        if m.equipe_domicile_id not in lignes or m.equipe_exterieur_id not in lignes:
            continue
        dom = lignes[m.equipe_domicile_id]
        ext = lignes[m.equipe_exterieur_id]

        dom.matchs_joues += 1
        ext.matchs_joues += 1
        dom.buts_marques += m.score_domicile
        dom.buts_encaisses += m.score_exterieur
        ext.buts_marques += m.score_exterieur
        ext.buts_encaisses += m.score_domicile

        if m.score_domicile > m.score_exterieur:
            dom.victoires += 1
            ext.defaites += 1
        elif m.score_domicile < m.score_exterieur:
            ext.victoires += 1
            dom.defaites += 1
        else:
            dom.nuls += 1
            ext.nuls += 1

    classement = list(lignes.values())
    classement.sort(key=lambda l: (-l.points, -l.difference_buts, -l.buts_marques))
    return classement
