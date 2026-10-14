from types import SimpleNamespace

import pytest

from app.routes.joueurs import _valeur_proposition_approuvee


class _FakeDb:
    async def get(self, _model, key):
        return SimpleNamespace(id=key)


@pytest.mark.asyncio
async def test_proposition_date_poste_club_et_nom_sont_convertis_avant_ecriture():
    joueur = SimpleNamespace(autorisation_parentale=True)
    db = _FakeDb()

    assert str(await _valeur_proposition_approuvee(db, joueur, "date_naissance", "1999-02-03")) == "1999-02-03"
    assert await _valeur_proposition_approuvee(db, joueur, "poste", "milieu") == "milieu"
    assert await _valeur_proposition_approuvee(db, joueur, "club_actuel_id", "42") == 42
    assert await _valeur_proposition_approuvee(db, joueur, "nom_complet", "Nom corrigé") == "Nom corrigé"
