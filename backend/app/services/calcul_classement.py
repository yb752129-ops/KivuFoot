"""Calcul du classement d'une saison.

Règles :
- toutes les inscriptions ``saison_clubs`` créent une ligne, initialisée à 0 ;
- seuls les matchs ``statut = valide`` modifient le classement ;
- un filtre de groupe lit ``saison_clubs.groupe``, jamais ``matchs.groupe`` ;
- points : victoire = 3, nul = 1, défaite = 0.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.club import Club
from app.models.competition import SaisonClub
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


async def calculer_classement(
    db: AsyncSession,
    saison_id: int,
    groupe: str | None = None,
) -> list[LigneClassement]:
    """Construit le classement depuis les inscriptions, puis applique les matchs valides."""
    inscriptions = await db.execute(
        select(SaisonClub, Club)
        .join(Club, Club.id == SaisonClub.club_id)
        .where(SaisonClub.saison_id == saison_id)
        .order_by(Club.nom, Club.id)
    )
    inscrits = inscriptions.all()

    groupe_value = getattr(groupe, "value", groupe)
    groupe_par_club = {lien.club_id: getattr(lien.groupe, "value", lien.groupe) for lien, _ in inscrits}
    if groupe_value:
        lignes_clubs = [(lien, club) for lien, club in inscrits if groupe_par_club.get(lien.club_id) == groupe_value]
    else:
        lignes_clubs = inscrits

    lignes: dict[int, LigneClassement] = {
        lien.club_id: LigneClassement(lien.club_id, club.nom)
        for lien, club in lignes_clubs
    }
    if not lignes:
        return []

    result = await db.execute(
        select(Match).where(
            Match.saison_id == saison_id,
            Match.statut == StatutMatch.VALIDE,
        )
    )
    matchs_valides = result.scalars().all()

    for match_ in matchs_valides:
        domicile_id = match_.equipe_domicile_id
        exterieur_id = match_.equipe_exterieur_id
        if domicile_id not in lignes or exterieur_id not in lignes:
            continue

        # En mode groupe, les deux équipes doivent appartenir à ce groupe
        # officiel. Match.groupe n'est volontairement jamais consulté ici.
        if groupe_value:
            if (
                groupe_par_club.get(domicile_id) != groupe_value
                or groupe_par_club.get(exterieur_id) != groupe_value
            ):
                continue

        dom = lignes[domicile_id]
        ext = lignes[exterieur_id]

        dom.matchs_joues += 1
        ext.matchs_joues += 1
        dom.buts_marques += match_.score_domicile
        dom.buts_encaisses += match_.score_exterieur
        ext.buts_marques += match_.score_exterieur
        ext.buts_encaisses += match_.score_domicile

        if match_.score_domicile > match_.score_exterieur:
            dom.victoires += 1
            ext.defaites += 1
        elif match_.score_domicile < match_.score_exterieur:
            ext.victoires += 1
            dom.defaites += 1
        else:
            dom.nuls += 1
            ext.nuls += 1

    classement = list(lignes.values())
    classement.sort(key=lambda ligne: (-ligne.points, -ligne.difference_buts, -ligne.buts_marques, ligne.club_nom))
    return classement
