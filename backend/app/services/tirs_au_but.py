from collections.abc import Iterable

PHASES_ELIMINATOIRES = frozenset({"barrage", "quart", "demi", "finale"})


def score_tirs_au_but(tirs: Iterable[dict] | None) -> dict[str, dict[str, int]]:
    score = {
        "domicile": {"tirs": 0, "marques": 0},
        "exterieur": {"tirs": 0, "marques": 0},
    }
    for tir in tirs or []:
        equipe = tir.get("equipe_concernee")
        resultat = tir.get("resultat")
        if equipe not in score:
            continue
        score[equipe]["tirs"] += 1
        if resultat == "marque":
            score[equipe]["marques"] += 1
    return score


def vainqueur_tirs_au_but(tirs: Iterable[dict] | None) -> str | None:
    """Retourne le côté qualifié dès que la séance est mathématiquement décidée."""
    score = score_tirs_au_but(tirs)
    home = score["domicile"]
    away = score["exterieur"]
    hn, an = home["tirs"], away["tirs"]
    hg, ag = home["marques"], away["marques"]

    # Série initiale de cinq tirs : arrêter dès qu'un côté ne peut plus être rejoint.
    if hn <= 5 and an <= 5:
        if hg > ag + (5 - an):
            return "domicile"
        if ag > hg + (5 - hn):
            return "exterieur"
        if hn == an == 5 and hg != ag:
            return "domicile" if hg > ag else "exterieur"
        return None

    # Mort subite : après une paire complète, le score doit départager.
    if hn == an and hn >= 5 and hg != ag:
        return "domicile" if hg > ag else "exterieur"
    # Si la paire est incomplète, un écart de deux buts rend le retour impossible.
    if hn == an + 1 and hg > ag + 1:
        return "domicile"
    if an == hn + 1 and ag > hg + 1:
        return "exterieur"
    return None
