"""Règles partagées pour les slots tactiques d'une composition."""


def slots_formation(formation: str | None) -> set[tuple[int, int]] | None:
    """Retourne les slots valides d'une formation à onze joueurs."""
    if not formation:
        return None
    nombres = [int(part) for part in str(formation).split("-") if part.isdigit() and int(part) > 0]
    if len(nombres) < 2 or sum(nombres) != 10:
        return None
    return {
        (ligne_index, position_index)
        for ligne_index, places in enumerate([1, *nombres])
        for position_index in range(places)
    }


def positions_titulaires_valides(formation: str | None, participations) -> bool:
    """Vérifie les 11 slots de titulaires sans dépendre du poste du joueur."""
    slots = slots_formation(formation)
    titulaires = [
        participation
        for participation in participations
        if getattr(getattr(participation, "statut", None), "value", getattr(participation, "statut", None)) == "titulaire"
    ]
    if slots is None or len(titulaires) != 11:
        return False
    places = []
    for participation in titulaires:
        ligne = getattr(participation, "ligne_index", None)
        position = getattr(participation, "position_index", None)
        if (ligne, position) not in slots:
            return False
        places.append((ligne, position))
    return len(set(places)) == 11
