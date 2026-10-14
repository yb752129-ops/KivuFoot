from datetime import datetime, timezone

import pytest

from app.services.documents_officiels import _match_pdf_bytes, _pdf_bytes


@pytest.mark.parametrize(
    "goals,discipline",
    [
        ([("17'", "Kimmich", "But"), ("73'", "Mbilizi", "But")], [("9'", "Samson", "Carton jaune")]),
        ([], []),
        ([("—", "Joueur avec un nom très long pour vérifier le retour à la ligne", "Penalty raté")], []),
    ],
)
def test_feuille_match_pdf_brandee_conserve_les_sections(goals, discipline):
    data = _match_pdf_bytes(
        competition="Tournoi Interdépartemental — 2e édition",
        edition="2e semestre 2026",
        matchday="J3",
        date_heure=datetime(2026, 10, 3, 13, 30, tzinfo=timezone.utc),
        stadium="Hope stadium",
        home="SANTÉ PUBLIQUE",
        away="G.G.T-GRF",
        score_home=1,
        score_away=1,
        goals=goals,
        discipline=discipline,
        man_of_match="Non désigné",
    )

    assert data.startswith(b"%PDF")
    assert len(data) > 10_000
    assert b"/Subtype /Image" in data


def test_pdf_generique_distingue_zero_et_donnee_absente():
    data = _pdf_bytes(
        "CONTROLE KIVUFOOT",
        [("Buts", 0), ("Minutes", None), ("Nom", "Joueur de contrôle")],
    )

    assert data.startswith(b"%PDF")
    assert len(data) > 10_000
    assert b"/Subtype /Image" in data
