"""Génération des documents à partir de données officiellement validées."""
from __future__ import annotations

import hashlib
import io
import json
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.actualite import HommeMatch
from app.models.club import Club
from app.models.competition import Competition, Saison
from app.models.enums import StatutMatch, StatutValidationEvenement, TypeEvenement
from app.models.evenement import EvenementMatch
from app.models.joueur import Joueur
from app.models.match import Match
from app.models.document import DocumentOfficiel
from app.models.stats import StatistiqueJoueur
from app.services.stockage_document import DepotDocumentRefus, uploader_document, url_publique


def _value(value):
    return value.value if hasattr(value, "value") else value


async def _version_document(
    db: AsyncSession,
    *,
    type_document: str,
    scope_id: int,
    saison_id: int | None,
) -> tuple[int, DocumentOfficiel | None]:
    query = select(DocumentOfficiel).where(
        DocumentOfficiel.type_document == type_document,
        DocumentOfficiel.scope_id == scope_id,
    )
    if saison_id is None:
        query = query.where(DocumentOfficiel.saison_id.is_(None))
    else:
        query = query.where(DocumentOfficiel.saison_id == saison_id)
    previous = (
        await db.execute(query.order_by(DocumentOfficiel.version.desc(), DocumentOfficiel.id.desc()).limit(1))
    ).scalar_one_or_none()
    max_version = await db.scalar(
        select(func.max(DocumentOfficiel.version)).where(
            DocumentOfficiel.type_document == type_document,
            DocumentOfficiel.scope_id == scope_id,
            DocumentOfficiel.saison_id == saison_id,
        )
    )
    return int(max_version or 0) + 1, previous


def _pdf_bytes(title: str, blocks: list[tuple[str, str]]) -> bytes:
    # Import tardif : le backend reste importable dans les environnements
    # d'audit qui n'ont pas encore installé la dépendance PDF.
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=title,
        author="KivuFoot",
    )
    styles = getSampleStyleSheet()
    heading = ParagraphStyle("KivuHeading", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=17, leading=22, textColor=colors.HexColor("#18324b"))
    label = ParagraphStyle("KivuLabel", parent=styles["BodyText"], fontSize=9, textColor=colors.HexColor("#506070"))
    value = ParagraphStyle("KivuValue", parent=styles["BodyText"], fontSize=10, leading=14)
    story = [Paragraph("KIVUFOOT", heading), Spacer(1, 4 * mm), Paragraph(title, styles["Heading2"]), Spacer(1, 5 * mm)]
    table_data = []
    for key, text in blocks:
        table_data.append([Paragraph(key, label), Paragraph(str(text or "Non renseigné"), value)])
    table = Table(table_data, colWidths=[48 * mm, 125 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#d9e1e8")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f2f6f8")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Données issues des éléments officiellement validés par KivuFoot. L'autorité sportive reste le Comité d'Organisation.", label))
    doc.build(story)
    return output.getvalue()


async def _match_context(db: AsyncSession, match: Match) -> tuple[Competition | None, Saison | None, Club | None, Club | None]:
    saison = await db.get(Saison, match.saison_id)
    competition = await db.get(Competition, saison.competition_id) if saison else None
    home = await db.get(Club, match.equipe_domicile_id) if match.equipe_domicile_id else None
    away = await db.get(Club, match.equipe_exterieur_id) if match.equipe_exterieur_id else None
    return competition, saison, home, away


async def generer_document_match(db: AsyncSession, match_id: int, user_id: int) -> tuple[DocumentOfficiel, bytes]:
    match = await db.get(Match, match_id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    if _value(match.statut) != StatutMatch.VALIDE.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "Un dossier officiel ne peut être généré que pour un match validé.")
    competition, saison, home, away = await _match_context(db, match)
    events = (
        await db.execute(
            select(EvenementMatch)
            .where(
                EvenementMatch.match_id == match.id,
                EvenementMatch.statut_validation == StatutValidationEvenement.VALIDE,
                EvenementMatch.refuse.is_(False),
            )
            .order_by(EvenementMatch.minute, EvenementMatch.id)
        )
    ).scalars().all()
    player_ids = {event.joueur_id for event in events if event.joueur_id} | {event.joueur_secondaire_id for event in events if event.joueur_secondaire_id}
    players = {}
    if player_ids:
        players = {row.id: row for row in (await db.execute(select(Joueur).where(Joueur.id.in_(player_ids)))).scalars().all()}
    facts = []
    for event in events:
        if _value(event.type) in ("but", "but_contre_son_camp", "penalty"):
            facts.append(f"{_value(event.type)} — {players.get(event.joueur_id).nom_complet if players.get(event.joueur_id) else 'Joueur non renseigné'} — {event.minute}'")
    cards = [
        f"{_value(event.type)} — {players.get(event.joueur_id).nom_complet if players.get(event.joueur_id) else 'Joueur non renseigné'} — {event.minute}'"
        for event in events
        if _value(event.type) in ("carton_jaune", "carton_rouge")
    ]
    homme = await db.scalar(select(HommeMatch).where(HommeMatch.match_id == match.id))
    homme_text = "Non désigné"
    if homme:
        homme_player = await db.get(Joueur, homme.joueur_id)
        homme_text = homme_player.nom_complet if homme_player else f"Joueur #{homme.joueur_id}"
    snapshot = {
        "match_id": match.id,
        "statut": _value(match.statut),
        "competition_id": competition.id if competition else None,
        "saison_id": saison.id if saison else None,
        "equipe_domicile_id": match.equipe_domicile_id,
        "equipe_exterieur_id": match.equipe_exterieur_id,
        "journee": match.journee,
        "date_heure": match.date_heure.isoformat() if match.date_heure else None,
        "stade": match.stade,
        "score": [match.score_domicile, match.score_exterieur],
        "events": [{"id": event.id, "type": _value(event.type), "minute": event.minute, "joueur_id": event.joueur_id} for event in events],
        "homme_du_match": homme.joueur_id if homme else None,
    }
    canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
    existing = await db.scalar(
        select(DocumentOfficiel).where(
            DocumentOfficiel.type_document == "match",
            DocumentOfficiel.scope_id == match.id,
            DocumentOfficiel.empreinte_source == fingerprint,
        )
    )
    if existing is not None and existing.statut == "publie":
        return existing, b""
    # Une ligne en erreur est conservée comme trace, mais une nouvelle
    # génération/version est autorisée après rétablissement du stockage.
    version, previous = await _version_document(
        db, type_document="match", scope_id=match.id, saison_id=saison.id if saison else None
    )
    title = "FEUILLE OFFICIELLE DU MATCH"
    blocks = [
        ("Rencontre", f"{home.nom if home else 'Domicile'} — {away.nom if away else 'Extérieur'}"),
        ("Résultat", f"{match.score_domicile} — {match.score_exterieur}"),
        ("Compétition", competition.nom if competition else "Non renseignée"),
        ("Édition", saison.nom if saison else "Non renseignée"),
        ("Journée", match.journee or "Non renseignée"),
        ("Date / stade", f"{match.date_heure.isoformat()} — {match.stade or 'Non renseigné'}"),
        ("Buteurs", "\n".join(facts) or "Aucun buteur renseigné"),
        ("Discipline", "\n".join(cards) or "Aucun carton"),
        ("Homme du match", homme_text),
    ]
    data = _pdf_bytes(title, blocks)
    document = DocumentOfficiel(
        type_document="match",
        scope_id=match.id,
        competition_id=competition.id if competition else None,
        saison_id=saison.id if saison else None,
        version=version,
        statut="genere",
        titre=title,
        empreinte_source=fingerprint,
        snapshot=snapshot,
        genere_par_id=user_id,
        remplace_document_id=previous.id if previous else None,
    )
    db.add(document)
    await db.flush()
    try:
        storage_key = f"matchs/{match.id}/v{document.version}.pdf"
        await uploader_document(storage_key, data)
        document.storage_key = storage_key
        document.statut = "publie"
        document.publie_par_id = user_id
        document.published_at = datetime.now(timezone.utc)
    except DepotDocumentRefus as exc:
        document.statut = "erreur"
        document.message_erreur = str(exc)
    return document, data


async def generer_document_joueur(db: AsyncSession, joueur_id: int, saison_id: int, user_id: int) -> tuple[DocumentOfficiel, bytes]:
    joueur = await db.get(Joueur, joueur_id)
    saison = await db.get(Saison, saison_id)
    if joueur is None or joueur.anonymise or joueur.fusionne:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Joueur introuvable.")
    if saison is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Édition introuvable.")
    stat = await db.scalar(select(StatistiqueJoueur).where(StatistiqueJoueur.joueur_id == joueur_id, StatistiqueJoueur.saison_id == saison_id))
    values = stat or StatistiqueJoueur(joueur_id=joueur_id, competition_id=saison.competition_id, saison_id=saison_id)
    snapshot = {
        "joueur_id": joueur_id,
        "joueur_nom": joueur.nom_complet,
        "club_actuel_id": joueur.club_actuel_id,
        "saison_id": saison_id,
        "saison_nom": saison.nom,
        "competition_id": saison.competition_id,
        "matchs_joues": values.matchs_joues,
        "titularisations": values.titularisations,
        "minutes_jouees": values.minutes_jouees,
        "buts": values.buts,
        "passes_decisives": values.passes_decisives,
        "cartons_jaunes": values.cartons_jaunes,
        "cartons_rouges": values.cartons_rouges,
    }
    canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
    existing = await db.scalar(select(DocumentOfficiel).where(DocumentOfficiel.type_document == "joueur", DocumentOfficiel.scope_id == joueur_id, DocumentOfficiel.saison_id == saison_id, DocumentOfficiel.empreinte_source == fingerprint))
    if existing is not None and existing.statut == "publie":
        return existing, b""
    # Une ligne en erreur est conservée comme trace, mais une nouvelle
    # génération/version est autorisée après rétablissement du stockage.
    version, previous = await _version_document(
        db, type_document="joueur", scope_id=joueur_id, saison_id=saison_id
    )
    title = "FICHE STATISTIQUE JOUEUR"
    data = _pdf_bytes(
        title,
        [
            ("Nom", joueur.nom_complet),
            ("Équipe actuelle", str(joueur.club_actuel_id or "Non renseignée")),
            ("Édition", saison.nom or "Non renseignée"),
            ("Matchs", values.matchs_joues),
            ("Titularisations", values.titularisations),
            ("Minutes", values.minutes_jouees),
            ("Buts", values.buts),
            ("Passes décisives", values.passes_decisives),
            ("Cartons jaunes", values.cartons_jaunes),
            ("Cartons rouges", values.cartons_rouges),
        ],
    )
    document = DocumentOfficiel(type_document="joueur", scope_id=joueur_id, competition_id=saison.competition_id, saison_id=saison_id, version=version, statut="genere", titre=title, empreinte_source=fingerprint, snapshot=snapshot, genere_par_id=user_id, remplace_document_id=previous.id if previous else None)
    db.add(document)
    await db.flush()
    try:
        storage_key = f"joueurs/{joueur_id}/saisons/{saison_id}/v{document.version}.pdf"
        await uploader_document(storage_key, data)
        document.storage_key = storage_key
        document.statut = "publie"
        document.publie_par_id = user_id
        document.published_at = datetime.now(timezone.utc)
    except DepotDocumentRefus as exc:
        document.statut = "erreur"
        document.message_erreur = str(exc)
    return document, data


async def document_url(document: DocumentOfficiel) -> str | None:
    return url_publique(document.storage_key) if document.storage_key and document.statut == "publie" else None
