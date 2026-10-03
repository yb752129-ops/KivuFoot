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
from app.services.reglements import get_reglement_actif


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
        self._points_victoire = 3
        self._points_nul = 1
        self._points_defaite = 0
        self._points_adjustment = 0

    def configurer_points(self, victoire: int | None, nul: int | None, defaite: int | None) -> None:
        if victoire is not None:
            self._points_victoire = victoire
        if nul is not None:
            self._points_nul = nul
        if defaite is not None:
            self._points_defaite = defaite

    @property
    def difference_buts(self) -> int:
        return self.buts_marques - self.buts_encaisses

    @property
    def points(self) -> int:
        return self.victoires * self._points_victoire + self.nuls * self._points_nul + self.defaites * self._points_defaite + self._points_adjustment

    def ajuster_points_forfait(self, victoire: int | None, defaite: int | None) -> None:
        if victoire is not None:
            self._points_adjustment += victoire - self._points_victoire
        if defaite is not None:
            self._points_adjustment += defaite - self._points_defaite


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

    # Les valeurs configurées par le règlement actif remplacent les valeurs
    # historiques du classement sans changer le comportement des éditions
    # legacy qui n'ont encore aucun règlement rattaché.
    reglement = await get_reglement_actif(db, saison_id)
    configuration = reglement.configuration if reglement else {}
    points = configuration.get("points", {}) if isinstance(configuration, dict) else {}
    if isinstance(points, dict):
        for ligne in lignes.values():
            ligne.configurer_points(points.get("victoire"), points.get("nul"), points.get("defaite"))

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
            vainqueur, perdant = dom, ext
        elif match_.score_domicile < match_.score_exterieur:
            ext.victoires += 1
            dom.defaites += 1
            vainqueur, perdant = ext, dom
        else:
            dom.nuls += 1
            ext.nuls += 1
            vainqueur = perdant = None

        if match_.forfait and vainqueur is not None:
            forfait_points = configuration.get("forfait", {}) if isinstance(configuration, dict) else {}
            if isinstance(forfait_points, dict):
                forfait_victoire = points.get("forfait_victoire") if isinstance(points, dict) else None
                forfait_defaite = points.get("forfait_defaite") if isinstance(points, dict) else None
                forfait_victoire = forfait_victoire if forfait_victoire is not None else forfait_points.get("victoire")
                forfait_defaite = forfait_defaite if forfait_defaite is not None else forfait_points.get("defaite")
                vainqueur.ajuster_points_forfait(forfait_victoire, forfait_defaite)
                perdant.ajuster_points_forfait(forfait_defaite, forfait_victoire)

    classement = list(lignes.values())
    departages = configuration.get("departages") if isinstance(configuration, dict) else None
    criteres = departages if isinstance(departages, list) and departages else ["points", "difference_buts", "buts_marques"]
    criteres_reconnus = [
        critere for critere in criteres
        if critere in {"points", "difference_buts", "buts_marques", "buts_encaisses", "victoires", "nuls", "defaites", "matchs_joues"}
    ] or ["points", "difference_buts", "buts_marques"]
    def cle_tri(ligne: LigneClassement):
        valeurs = []
        for critere in criteres_reconnus:
            valeur = {
                "points": ligne.points,
                "difference_buts": ligne.difference_buts,
                "buts_marques": ligne.buts_marques,
                "buts_encaisses": ligne.buts_encaisses,
                "victoires": ligne.victoires,
                "nuls": ligne.nuls,
                "defaites": ligne.defaites,
                "matchs_joues": ligne.matchs_joues,
            }.get(critere)
            if valeur is not None:
                valeurs.append(-valeur)
        valeurs.append(ligne.club_nom)
        return tuple(valeurs)

    classement.sort(key=cle_tri)
    return classement
