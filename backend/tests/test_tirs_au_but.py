import pytest
from pydantic import ValidationError

from app.schemas.match import TirAuButCreate
from app.services.tirs_au_but import vainqueur_tirs_au_but


def test_shootout_attempt_schema_requires_player():
    tir = TirAuButCreate(equipe_concernee="domicile", joueur_id=12, resultat="marque")
    assert tir.equipe_concernee.value == "domicile"
    assert tir.joueur_id == 12
    assert tir.resultat == "marque"
    with pytest.raises(ValidationError):
        TirAuButCreate(equipe_concernee="domicile", resultat="marque")


def test_shootout_attempt_rejects_unknown_result():
    with pytest.raises(ValidationError):
        TirAuButCreate(equipe_concernee="domicile", resultat="but")


def test_shootout_winner_after_five_each():
    tirs = []
    outcomes = ["marque", "rate", "marque", "marque", "rate", "marque", "marque", "rate", "rate", "rate"]
    for i, resultat in enumerate(outcomes):
        tirs.append({"ordre": i + 1, "equipe_concernee": "domicile" if i % 2 == 0 else "exterieur", "resultat": resultat})
    assert vainqueur_tirs_au_but(tirs) == "domicile"


def test_shootout_requires_sudden_death_when_five_each_tied():
    tirs = []
    for i in range(10):
        tirs.append({"ordre": i + 1, "equipe_concernee": "domicile" if i % 2 == 0 else "exterieur", "resultat": "marque"})
    assert vainqueur_tirs_au_but(tirs) is None
    tirs.extend([
        {"ordre": 11, "equipe_concernee": "domicile", "resultat": "marque"},
        {"ordre": 12, "equipe_concernee": "exterieur", "resultat": "rate"},
    ])
    assert vainqueur_tirs_au_but(tirs) == "domicile"
