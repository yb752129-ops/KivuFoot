from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.rbac import CLUB_ROLES, isClubRole, require_roles
from app.database import get_db
from app.models.actualite import HommeMatch
from app.models.club import Club
from app.models.enums import (
    EquipeConcernee,
    ResultatPenalty,
    RoleUtilisateur,
    StatutMatch,
    StatutParticipation,
    StatutValidationEvenement,
    TypeEvenement,
)
from app.models.evenement import EvenementMatch
from app.models.joueur import Joueur
from app.models.match import Match, MatchParticipation
from app.models.stats import StatistiqueJoueur
from app.models.user import User
from app.schemas.sync import TopStatLigne

router = APIRouter(prefix="/stats", tags=["Statistiques"])


def _valeur_enum(value):
    return value.value if hasattr(value, "value") else value


@router.get("/joueur/{joueur_id}/public")
async def stats_joueur_public(
    joueur_id: int,
    saison_id: int,
    db: AsyncSession = Depends(get_db),
):
    joueur = await db.get(Joueur, joueur_id)
    if joueur is None or joueur.anonymise or joueur.fusionne:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Joueur introuvable.")
    stat = await db.scalar(
        select(StatistiqueJoueur).where(
            StatistiqueJoueur.joueur_id == joueur_id,
            StatistiqueJoueur.saison_id == saison_id,
        )
    )
    buts_penaltys = await db.execute(
        select(EvenementMatch.resultat, EvenementMatch.id)
        .join(Match, Match.id == EvenementMatch.match_id)
        .where(
            Match.saison_id == saison_id,
            Match.statut == StatutMatch.VALIDE,
            EvenementMatch.joueur_id == joueur_id,
            EvenementMatch.type == TypeEvenement.PENALTY,
            EvenementMatch.statut_validation == StatutValidationEvenement.VALIDE,
            EvenementMatch.refuse.is_(False),
        )
    )
    penalty_rows = buts_penaltys.all()
    participation_rows = (
        await db.execute(
            select(MatchParticipation)
            .join(Match, Match.id == MatchParticipation.match_id)
            .where(
                Match.saison_id == saison_id,
                Match.statut == StatutMatch.VALIDE,
                MatchParticipation.joueur_id == joueur_id,
            )
        )
    ).scalars().all()
    evenement_rows = (
        await db.execute(
            select(EvenementMatch)
            .join(Match, Match.id == EvenementMatch.match_id)
            .where(
                Match.saison_id == saison_id,
                Match.statut == StatutMatch.VALIDE,
                or_(
                    EvenementMatch.joueur_id == joueur_id,
                    EvenementMatch.joueur_secondaire_id == joueur_id,
                ),
                EvenementMatch.statut_validation == StatutValidationEvenement.VALIDE,
                EvenementMatch.refuse.is_(False),
            )
        )
    ).scalars().all()
    homme_du_match = await db.scalar(
        select(func.count(HommeMatch.id))
        .join(Match, Match.id == HommeMatch.match_id)
        .where(
            Match.saison_id == saison_id,
            Match.statut == StatutMatch.VALIDE,
            HommeMatch.joueur_id == joueur_id,
        )
    )
    # Une ligne StatistiqueJoueur signifie qu'une donnée confirmée a été
    # produite par le flux de validation. En son absence, ne renvoyons pas
    # un faux tableau rempli de zéros : zéro et donnée indisponible ne sont
    # pas la même information.
    penalties_marques = sum(
        1 for resultat, _ in penalty_rows if _valeur_enum(resultat) == ResultatPenalty.MARQUE.value
    )
    penalties_rates = sum(
        1 for resultat, _ in penalty_rows if _valeur_enum(resultat) == ResultatPenalty.RATE.value
    )
    participation_confirmee = bool(participation_rows)
    buts_evenements = sum(
        1
        for evenement in evenement_rows
        if evenement.joueur_id == joueur_id
        and _valeur_enum(evenement.type) == TypeEvenement.BUT.value
    )
    passes_evenements = sum(
        1
        for evenement in evenement_rows
        if evenement.joueur_secondaire_id == joueur_id
        and _valeur_enum(evenement.type) == TypeEvenement.PASSE_DECISIVE.value
    )
    cartons_jaunes_evenements = sum(
        1
        for evenement in evenement_rows
        if evenement.joueur_id == joueur_id
        and _valeur_enum(evenement.type) == TypeEvenement.CARTON_JAUNE.value
    )
    cartons_rouges_evenements = sum(
        1
        for evenement in evenement_rows
        if evenement.joueur_id == joueur_id
        and _valeur_enum(evenement.type) == TypeEvenement.CARTON_ROUGE.value
    )
    buts_evenements += penalties_marques
    participations_matchs = len({participation.match_id for participation in participation_rows})
    participations_titulaires = sum(
        1
        for participation in participation_rows
        if _valeur_enum(participation.statut) == StatutParticipation.TITULAIRE.value
    )
    # `minute_sortie=NULL` ne prouve pas qu'un joueur a joué 90 minutes :
    # l'ancienne feuille de match ne distinguait pas « fin de match connue »
    # et « minutes non collectées ». La vue publique choisit donc l'option
    # honnête : les minutes restent nulles tant que chaque borne n'est pas
    # effectivement renseignée. Une saisie connue jusqu'à la fin doit utiliser
    # minute_sortie=90.
    minutes_collectees = bool(participation_rows) and all(
        participation.minute_sortie is not None for participation in participation_rows
    )
    participations_minutes = (
        sum(
            max(0, participation.minute_sortie - participation.minute_entree)
            for participation in participation_rows
        )
        if minutes_collectees
        else None
    )
    champs_stats = (
        "matchs_joues",
        "titularisations",
        "minutes_jouees",
        "buts",
        "passes_decisives",
        "cartons_jaunes",
        "cartons_rouges",
        "penalties_marques",
        "penalties_rates",
        "hommes_du_match",
    )

    if stat is None:
        # Les penalties ratés et les désignations homme du match possèdent
        # leurs propres tables officielles. Ils peuvent donc être publiés
        # même si aucune ligne d'agrégat joueur n'existe encore.
        statuts = {champ: "NON_DISPONIBLE" for champ in champs_stats}
        if participation_confirmee:
            statuts = {champ: "CONFIRMEE" for champ in champs_stats}
            if not minutes_collectees:
                statuts["minutes_jouees"] = "NON_DISPONIBLE"
        else:
            if buts_evenements:
                statuts["buts"] = "CONFIRMEE"
            if passes_evenements:
                statuts["passes_decisives"] = "CONFIRMEE"
            if cartons_jaunes_evenements:
                statuts["cartons_jaunes"] = "CONFIRMEE"
            if cartons_rouges_evenements:
                statuts["cartons_rouges"] = "CONFIRMEE"
            if penalty_rows:
                statuts["penalties_marques"] = "CONFIRMEE"
                statuts["penalties_rates"] = "CONFIRMEE"
            if homme_du_match:
                statuts["hommes_du_match"] = "CONFIRMEE"
        au_moins_une_donnee = any(statut == "CONFIRMEE" for statut in statuts.values())
        return {
            "joueur_id": joueur.id,
            "joueur_nom": joueur.nom_complet,
            "club_actuel_id": joueur.club_actuel_id,
            "saison_id": saison_id,
            "disponible": au_moins_une_donnee,
            "statut": "CONFIRMEE" if au_moins_une_donnee else "NON_DISPONIBLE",
            "message": (
                (
                    "Certaines données confirmées sont publiées ; les autres restent indisponibles. "
                    "Les données provisoires ne sont pas publiées faute de source publique fiable."
                )
                if au_moins_une_donnee
                else (
                    "Aucune statistique confirmée pour cette édition. "
                    "Les données provisoires ne sont pas publiées faute de source publique fiable."
                )
            ),
            "matchs_joues": participations_matchs if participation_confirmee else None,
            "titularisations": participations_titulaires if participation_confirmee else None,
            "minutes_jouees": participations_minutes if participation_confirmee else None,
            "buts": buts_evenements if participation_confirmee or buts_evenements else None,
            "passes_decisives": passes_evenements if participation_confirmee or passes_evenements else None,
            "cartons_jaunes": cartons_jaunes_evenements if participation_confirmee or cartons_jaunes_evenements else None,
            "cartons_rouges": cartons_rouges_evenements if participation_confirmee or cartons_rouges_evenements else None,
            "penalties_marques": penalties_marques if participation_confirmee or penalty_rows else None,
            "penalties_rates": penalties_rates if participation_confirmee or penalty_rows else None,
            "hommes_du_match": int(homme_du_match) if participation_confirmee or homme_du_match else None,
            "statuts": statuts,
            "source": "matchs_officiellement_valides" if au_moins_une_donnee else "aucune_donnee_confirmee",
            "donnees_non_collectees": [
                "Statistiques défensives détaillées",
                "Arrêts et buts évités du gardien",
            ],
        }

    if participation_confirmee:
        # Les tables de faits sont la source publique de vérité. Même si un
        # agrégat historique existe, ne le réutilisons pas aveuglément : il
        # pourrait dater d'avant le marquage refuse=true d'un événement.
        valeurs = {
            "matchs_joues": participations_matchs,
            "titularisations": participations_titulaires,
            "minutes_jouees": participations_minutes,
            "buts": buts_evenements,
            "passes_decisives": passes_evenements,
            "cartons_jaunes": cartons_jaunes_evenements,
            "cartons_rouges": cartons_rouges_evenements,
            "penalties_marques": penalties_marques,
            "penalties_rates": penalties_rates,
            "hommes_du_match": int(homme_du_match or 0),
        }
        statuts = {champ: "CONFIRMEE" for champ in champs_stats}
        if not minutes_collectees:
            statuts["minutes_jouees"] = "NON_DISPONIBLE"
        valeurs["minutes_jouees"] = participations_minutes
    else:
        valeurs = {
            "matchs_joues": None,
            "titularisations": None,
            "minutes_jouees": None,
            "buts": buts_evenements if buts_evenements else None,
            "passes_decisives": passes_evenements if passes_evenements else None,
            "cartons_jaunes": cartons_jaunes_evenements if cartons_jaunes_evenements else None,
            "cartons_rouges": cartons_rouges_evenements if cartons_rouges_evenements else None,
            "penalties_marques": penalties_marques if penalty_rows else None,
            "penalties_rates": penalties_rates if penalty_rows else None,
            "hommes_du_match": int(homme_du_match) if homme_du_match else None,
        }
        statuts = {champ: "NON_DISPONIBLE" for champ in champs_stats}
        if buts_evenements:
            statuts["buts"] = "CONFIRMEE"
        if passes_evenements:
            statuts["passes_decisives"] = "CONFIRMEE"
        if cartons_jaunes_evenements:
            statuts["cartons_jaunes"] = "CONFIRMEE"
        if cartons_rouges_evenements:
            statuts["cartons_rouges"] = "CONFIRMEE"
        if penalty_rows:
            statuts["penalties_marques"] = "CONFIRMEE"
            statuts["penalties_rates"] = "CONFIRMEE"
        if homme_du_match:
            statuts["hommes_du_match"] = "CONFIRMEE"

    au_moins_une_donnee = participation_confirmee or any(
        (
            buts_evenements,
            passes_evenements,
            cartons_jaunes_evenements,
            cartons_rouges_evenements,
            penalty_rows,
            homme_du_match,
        )
    )
    return {
        "joueur_id": joueur.id,
        "joueur_nom": joueur.nom_complet,
        "club_actuel_id": joueur.club_actuel_id,
        "saison_id": saison_id,
        "disponible": au_moins_une_donnee,
        "statut": "CONFIRMEE" if au_moins_une_donnee else "NON_DISPONIBLE",
        "message": (
            "Statistiques calculées à partir des données confirmées de la compétition."
            if participation_confirmee
            else (
                "Certaines données confirmées sont publiées ; les autres restent indisponibles. "
                "Les données provisoires ne sont pas publiées faute de source publique fiable."
                if au_moins_une_donnee
                else (
                    "Aucune statistique confirmée pour cette édition. "
                    "Les données provisoires ne sont pas publiées faute de source publique fiable."
                )
            )
        ),
        **valeurs,
        "statuts": statuts,
        "source": "matchs_officiellement_valides" if au_moins_une_donnee else "aucune_donnee_confirmee",
        "donnees_non_collectees": [
            "Statistiques défensives détaillées",
            "Arrêts et buts évités du gardien",
        ],
    }


@router.get("/joueur/{joueur_id}/public/matchs")
async def stats_joueur_matchs_public(
    joueur_id: int,
    saison_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Historique public limité aux matchs officiellement validés.

    Cette vue est reconstruite à partir des feuilles de match et des
    événements validés. Elle ne publie pas les matchs en cours ou terminés
    mais encore non validés, et ne modifie aucun agrégat historique.
    """
    joueur = await db.get(Joueur, joueur_id)
    if joueur is None or joueur.anonymise or joueur.fusionne:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Joueur introuvable.")

    result = await db.execute(
        select(Match)
        .options(selectinload(Match.equipe_domicile), selectinload(Match.equipe_exterieur))
        .where(Match.saison_id == saison_id, Match.statut == StatutMatch.VALIDE)
        .order_by(Match.date_heure.desc(), Match.id.desc())
        .limit(200)
    )
    matchs = result.scalars().all()
    match_ids = [match.id for match in matchs]

    if not match_ids:
        return {
            "joueur_id": joueur.id,
            "saison_id": saison_id,
            "disponible": False,
            "statut": "NON_DISPONIBLE",
            "message": (
                "Aucun match officiellement validé pour cette édition. "
                "Les données provisoires ne sont pas publiées faute de source publique fiable."
            ),
            "source": "aucune_donnee_confirmee",
            "matchs": [],
        }

    participations = (
        await db.execute(
            select(MatchParticipation).where(
                MatchParticipation.match_id.in_(match_ids),
                MatchParticipation.joueur_id == joueur_id,
            )
        )
    ).scalars().all()
    participations_by_match = {participation.match_id: participation for participation in participations}

    evenements = (
        await db.execute(
            select(EvenementMatch).where(
                EvenementMatch.match_id.in_(match_ids),
                or_(
                    EvenementMatch.joueur_id == joueur_id,
                    EvenementMatch.joueur_secondaire_id == joueur_id,
                ),
                EvenementMatch.statut_validation == StatutValidationEvenement.VALIDE,
                EvenementMatch.refuse.is_(False),
            )
        )
    ).scalars().all()
    evenements_by_match: dict[int, list[EvenementMatch]] = {}
    for evenement in evenements:
        evenements_by_match.setdefault(evenement.match_id, []).append(evenement)

    hommes = (
        await db.execute(
            select(HommeMatch).where(
                HommeMatch.match_id.in_(match_ids),
                HommeMatch.joueur_id == joueur_id,
            )
        )
    ).scalars().all()
    hommes_by_match = {homme.match_id: homme for homme in hommes}

    def valeur_enum(value):
        return value.value if hasattr(value, "value") else value

    def nom_club(club):
        return club.nom if club is not None else None

    lignes = []
    for match in matchs:
        participation = participations_by_match.get(match.id)
        match_events = evenements_by_match.get(match.id, [])
        homme = hommes_by_match.get(match.id)
        # Un match validé n'est pas, à lui seul, une participation du joueur.
        # Ne publions donc pas les matchs sans feuille de match, événement
        # validé non refusé ou désignation officielle Homme du match.
        if participation is None and not match_events and homme is None:
            continue
        side = valeur_enum(participation.equipe_concernee) if participation else None
        if side not in (EquipeConcernee.DOMICILE.value, EquipeConcernee.EXTERIEUR.value):
            side = next(
                (
                    valeur_enum(event.equipe_concernee)
                    for event in match_events
                    if valeur_enum(event.equipe_concernee)
                    in (EquipeConcernee.DOMICILE.value, EquipeConcernee.EXTERIEUR.value)
                ),
                None,
            )
        if side is None and homme is not None:
            if homme.club_id == match.equipe_domicile_id:
                side = EquipeConcernee.DOMICILE.value
            elif homme.club_id == match.equipe_exterieur_id:
                side = EquipeConcernee.EXTERIEUR.value

        if side == EquipeConcernee.DOMICILE.value:
            club = match.equipe_domicile
            adversaire = match.equipe_exterieur
            score_equipe = match.score_domicile
            score_adversaire = match.score_exterieur
        elif side == EquipeConcernee.EXTERIEUR.value:
            club = match.equipe_exterieur
            adversaire = match.equipe_domicile
            score_equipe = match.score_exterieur
            score_adversaire = match.score_domicile
        else:
            club = None
            adversaire = None
            score_equipe = None
            score_adversaire = None

        buts = 0
        passes = 0
        cartons_jaunes = 0
        cartons_rouges = 0
        penalties_marques = 0
        penalties_rates = 0
        presence_but = False
        presence_passe = False
        presence_carton_jaune = False
        presence_carton_rouge = False
        presence_penalty = False

        for evenement in match_events:
            type_evenement = valeur_enum(evenement.type)
            resultat_penalty = valeur_enum(evenement.resultat)
            if evenement.joueur_id == joueur_id and type_evenement == TypeEvenement.BUT.value:
                buts += 1
                presence_but = True
            elif (
                evenement.joueur_id == joueur_id
                and type_evenement == TypeEvenement.PENALTY.value
                and resultat_penalty == ResultatPenalty.MARQUE.value
            ):
                buts += 1
                penalties_marques += 1
                presence_but = True
                presence_penalty = True
            elif (
                evenement.joueur_id == joueur_id
                and type_evenement == TypeEvenement.PENALTY.value
                and resultat_penalty == ResultatPenalty.RATE.value
            ):
                penalties_rates += 1
                presence_penalty = True
            elif evenement.joueur_secondaire_id == joueur_id and type_evenement == TypeEvenement.PASSE_DECISIVE.value:
                passes += 1
                presence_passe = True
            elif evenement.joueur_id == joueur_id and type_evenement == TypeEvenement.CARTON_JAUNE.value:
                cartons_jaunes += 1
                presence_carton_jaune = True
            elif evenement.joueur_id == joueur_id and type_evenement == TypeEvenement.CARTON_ROUGE.value:
                cartons_rouges += 1
                presence_carton_rouge = True

        if participation is not None:
            minutes = (
                max(0, participation.minute_sortie - participation.minute_entree)
                if participation.minute_sortie is not None
                else None
            )
            participation_data = {
                "disponible": True,
                "statut": "CONFIRMEE",
                "titulaire": valeur_enum(participation.statut) == StatutParticipation.TITULAIRE.value,
                "minutes": minutes,
            }
            stats_status = {
                "participation": "CONFIRMEE",
                "minutes": "CONFIRMEE" if minutes is not None else "NON_DISPONIBLE",
                "buts": "CONFIRMEE",
                "passes_decisives": "CONFIRMEE",
                "cartons_jaunes": "CONFIRMEE",
                "cartons_rouges": "CONFIRMEE",
                "penalties": "CONFIRMEE",
                "homme_du_match": "CONFIRMEE",
            }
        else:
            participation_data = {
                "disponible": False,
                "statut": "NON_DISPONIBLE",
                "titulaire": None,
                "minutes": None,
            }
            stats_status = {
                "participation": "NON_DISPONIBLE",
                "minutes": "NON_DISPONIBLE",
                "buts": "CONFIRMEE" if presence_but else "NON_DISPONIBLE",
                "passes_decisives": "CONFIRMEE" if presence_passe else "NON_DISPONIBLE",
                "cartons_jaunes": "CONFIRMEE" if presence_carton_jaune else "NON_DISPONIBLE",
                "cartons_rouges": "CONFIRMEE" if presence_carton_rouge else "NON_DISPONIBLE",
                "penalties": "CONFIRMEE" if presence_penalty else "NON_DISPONIBLE",
                "homme_du_match": "CONFIRMEE" if homme is not None else "NON_DISPONIBLE",
            }

        lignes.append(
            {
                "match_id": match.id,
                "date_heure": match.date_heure,
                "journee": match.journee,
                "statut": "CONFIRMEE",
                "source": "match_officiellement_valide",
                "equipe_concernee": side,
                "club_nom": nom_club(club),
                "adversaire_nom": nom_club(adversaire),
                "score_equipe": score_equipe,
                "score_adversaire": score_adversaire,
                "participation": participation_data,
                "statistiques": {
                    "buts": buts if participation is not None or presence_but else None,
                    "passes_decisives": passes if participation is not None or presence_passe else None,
                    "cartons_jaunes": cartons_jaunes if participation is not None or presence_carton_jaune else None,
                    "cartons_rouges": cartons_rouges if participation is not None or presence_carton_rouge else None,
                    "penalties_marques": penalties_marques if participation is not None or presence_penalty else None,
                    "penalties_rates": penalties_rates if participation is not None or presence_penalty else None,
                },
                "homme_du_match": (homme is not None) if participation is not None or homme is not None else None,
                "statuts": stats_status,
            }
        )

    return {
        "joueur_id": joueur.id,
        "saison_id": saison_id,
        "disponible": bool(lignes),
        "statut": "CONFIRMEE" if lignes else "NON_DISPONIBLE",
        "message": "Historique construit à partir des matchs officiellement validés.",
        "source": "matchs_officiellement_valides",
        "matchs": lignes,
    }


@router.get("/joueur/{joueur_id}")
async def stats_joueur(
    joueur_id: int,
    saison_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR, *CLUB_ROLES)
    ),
):
    """Protected detailed stats; a club portal account sees its club only."""
    joueur = await db.get(Joueur, joueur_id)
    if joueur is None or joueur.anonymise or joueur.fusionne:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Joueur introuvable.")
    if isClubRole(current_user.role):
        if current_user.club_id != joueur.club_actuel_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Vous ne gérez pas ce joueur.")
    result = await db.execute(
        select(StatistiqueJoueur).where(
            StatistiqueJoueur.joueur_id == joueur_id, StatistiqueJoueur.saison_id == saison_id
        )
    )
    stats = result.scalars().all()
    if not stats:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucune statistique pour ce joueur sur cette saison.")
    return stats


async def _top(db: AsyncSession, saison_id: int, colonne, limit: int) -> list[TopStatLigne]:
    # Les tops publics sont recalculés depuis les événements officiels, et
    # non lus aveuglément dans un agrégat historique. Cela garantit qu'un
    # événement refuse ne peut pas rester visible après une correction.
    if colonne.key == "buts":
        joueur_colonne = EvenementMatch.joueur_id
        type_filter = or_(
            EvenementMatch.type == TypeEvenement.BUT,
            and_(
                EvenementMatch.type == TypeEvenement.PENALTY,
                EvenementMatch.resultat == ResultatPenalty.MARQUE,
            ),
        )
    elif colonne.key == "passes_decisives":
        joueur_colonne = EvenementMatch.joueur_secondaire_id
        type_filter = EvenementMatch.type == TypeEvenement.PASSE_DECISIVE
    else:
        return []

    valeur = func.count(EvenementMatch.id).label("valeur")
    result = await db.execute(
        select(Joueur, Club, valeur)
        .join(EvenementMatch, joueur_colonne == Joueur.id)
        .join(Match, Match.id == EvenementMatch.match_id)
        .outerjoin(Club, Club.id == Joueur.club_actuel_id)
        .options(selectinload(Joueur.photo_actuelle_rel))
        .where(
            Match.saison_id == saison_id,
            Match.statut == StatutMatch.VALIDE,
            EvenementMatch.statut_validation == StatutValidationEvenement.VALIDE,
            EvenementMatch.refuse.is_(False),
            joueur_colonne.is_not(None),
            type_filter,
            Joueur.anonymise.is_(False),
            Joueur.fusionne.is_(False),
        )
        .group_by(Joueur.id, Club.id)
        .order_by(valeur.desc(), Joueur.nom_complet.asc())
        .limit(min(limit, 50))
    )
    return [
        TopStatLigne(
            joueur_id=joueur.id,
            joueur_nom=joueur.nom_complet,
            club_id=club.id if club else None,
            club_nom=club.nom if club else None,
            photo_url=joueur.photo_url,
            valeur=int(total),
        )
        for joueur, club, total in result.all()
    ]


@router.get("/meilleurs-buteurs", response_model=list[TopStatLigne])
async def meilleurs_buteurs(saison_id: int, db: AsyncSession = Depends(get_db), limit: int = 10):
    return await _top(db, saison_id, StatistiqueJoueur.buts, limit)


@router.get("/meilleurs-passeurs", response_model=list[TopStatLigne])
async def meilleurs_passeurs(saison_id: int, db: AsyncSession = Depends(get_db), limit: int = 10):
    return await _top(db, saison_id, StatistiqueJoueur.passes_decisives, limit)
