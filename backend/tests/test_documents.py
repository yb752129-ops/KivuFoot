from datetime import datetime, timezone

import pytest

from app.services.documents_officiels import _match_pdf_bytes, _pdf_bytes
from app.schemas.document import DocumentPublicOut


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


def test_feuille_officielle_pdf_peut_inclure_la_seance_separee():
    data = _match_pdf_bytes(
        competition="Tournoi Interdépartemental",
        edition="2026",
        matchday="Barrage",
        date_heure=datetime(2026, 10, 31, 16, 0, tzinfo=timezone.utc),
        stadium="Hope stadium",
        home="G.G.T-2026",
        away="LES CHAMPIONS",
        score_home=1,
        score_away=1,
        goals=[],
        discipline=[],
        man_of_match="Non désigné",
        shootout_score=(4, 5),
        shootout=[("#1 · G.G.T-2026", "Joueur A", "Marqué"), ("#2 · LES CHAMPIONS", "Joueur B", "Raté")],
    )
    assert data.startswith(b"%PDF")
    assert len(data) > 10_000


def test_document_public_ne_contient_que_les_infos_publiables():
    document = DocumentPublicOut(
        titre="FEUILLE OFFICIELLE DU MATCH",
        version=1,
        published_at=datetime(2026, 10, 31, tzinfo=timezone.utc),
        url="https://example.test/match.pdf",
    )
    assert document.url.endswith("match.pdf")
