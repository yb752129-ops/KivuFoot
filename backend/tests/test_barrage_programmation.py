import pytest
from pydantic import ValidationError

from app.schemas.match import MatchCreate


def _payload(**overrides):
    base = {
        "saison_id": 1,
        "equipe_domicile_id": 10,
        "equipe_exterieur_id": 20,
        "phase": "barrage",
        "date_heure": None,
    }
    base.update(overrides)
    return base


def test_barrage_can_be_published_without_kickoff():
    match = MatchCreate(**_payload())
    assert match.phase == "barrage"
    assert match.date_heure is None


def test_non_barrage_still_requires_kickoff():
    with pytest.raises(ValidationError, match="date et l’heure sont obligatoires"):
        MatchCreate(**_payload(phase="poule"))
