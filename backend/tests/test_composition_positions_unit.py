import pytest
from fastapi import HTTPException

from app.routes.matchs import _composition_lignes, _valider_positions_composition
from app.schemas.match import CompositionEquipeIn


def _payload(formation):
    lignes = _composition_lignes(formation)
    slots = [(ligne, position) for ligne, places in enumerate(lignes) for position in range(places)]
    return CompositionEquipeIn(
        equipe="domicile",
        formation=formation,
        joueurs=[
            {
                "joueur_id": index + 1,
                "statut": "titulaire",
                "numero": index + 1,
                "ligne_index": ligne,
                "position_index": position,
            }
            for index, (ligne, position) in enumerate(slots)
        ],
    )


@pytest.mark.parametrize("formation", ["4-2-3-1", "4-3-3", "4-4-2"])
def test_formation_expose_exactement_onze_positions(formation):
    payload = _payload(formation)
    _valider_positions_composition(payload)
    assert len(payload.joueurs) == 11


def test_collision_de_position_refusee_sans_reaffectation():
    payload = _payload("4-3-3")
    payload.joueurs[1].ligne_index = payload.joueurs[0].ligne_index
    payload.joueurs[1].position_index = payload.joueurs[0].position_index
    with pytest.raises(HTTPException, match="déjà occupée"):
        _valider_positions_composition(payload)


def test_titulaire_sans_position_refuse():
    payload = _payload("4-3-3")
    payload.joueurs[3].ligne_index = None
    payload.joueurs[3].position_index = None
    with pytest.raises(HTTPException, match="position tactique explicite"):
        _valider_positions_composition(payload)
