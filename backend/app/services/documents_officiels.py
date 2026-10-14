"""Génération des documents à partir de données officiellement validées."""
from __future__ import annotations

import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

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
from app.config import settings


PDF_LAYOUT_VERSION = 2


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


def _pdf_value(value):
    # None signifie absence de collecte; zéro reste une valeur officielle.
    return "Non disponible" if value is None or value == "" else str(value)


def _pdf_contact() -> tuple[str, str, str, str]:
    """Identité PDF confirmée, sans dépendre d'une identité de bootstrap."""
    return (
        settings.pdf_contact_name or "Yves Bukasa",
        settings.pdf_contact_email or "yb752129@gmail.com",
        settings.pdf_contact_phone or "+257 64504091",
        settings.pdf_contact_whatsapp or "+243 983753771",
    )


def _pdf_logo_path() -> Path:
    configured = Path(settings.pdf_logo_path) if settings.pdf_logo_path else None
    if configured and configured.is_file():
        return configured
    return Path(__file__).resolve().parents[1] / "assets" / "kivufoot-logo.png"


def _pdf_paragraph(text, style):
    from reportlab.platypus import Paragraph

    return Paragraph(escape(_pdf_value(text)).replace("\n", "<br/>"), style)


def _pdf_document(output, title, footer_contact):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate

    def draw_footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(PDF_LINE)
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, 11 * mm, A4[0] - doc.rightMargin, 11 * mm)
        canvas.setFillColor(PDF_MUTED)
        canvas.setFont("Helvetica", 6.3)
        canvas.drawString(doc.leftMargin, 6.5 * mm, footer_contact)
        canvas.drawRightString(A4[0] - doc.rightMargin, 6.5 * mm, f"KivuFoot · Page {doc.page}")
        canvas.restoreState()

    return SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=13 * mm,
        bottomMargin=17 * mm,
        title=title,
        author="KivuFoot",
        subject="Document officiel de compétition",
        creator="KivuFoot",
        onFirstPage=draw_footer,
        onLaterPages=draw_footer,
    )


# Palette alignée sur l'interface KivuFoot : vert profond, vert vif et crème.
PDF_DARK = None
PDF_GREEN = None
PDF_LIME = None
PDF_CREAM = None
PDF_INK = None
PDF_MUTED = None
PDF_LINE = None
PDF_SOFT = None


def _pdf_palette():
    """Initialise la palette après l'import tardif de reportlab."""
    global PDF_DARK, PDF_GREEN, PDF_LIME, PDF_CREAM, PDF_INK, PDF_MUTED, PDF_LINE, PDF_SOFT
    from reportlab.lib import colors

    PDF_DARK = colors.HexColor("#073B2D")
    PDF_GREEN = colors.HexColor("#08A86B")
    PDF_LIME = colors.HexColor("#B9F34A")
    PDF_CREAM = colors.HexColor("#F6F3EA")
    PDF_INK = colors.HexColor("#15221F")
    PDF_MUTED = colors.HexColor("#64716C")
    PDF_LINE = colors.HexColor("#D7E1DC")
    PDF_SOFT = colors.HexColor("#EFF6F1")


def _pdf_styles():
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

    styles = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle(
            "KivuBrand", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=13,
            leading=15, textColor=PDF_LIME, alignment=TA_LEFT,
        ),
        "header_title": ParagraphStyle(
            "KivuHeaderTitle", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=15,
            leading=18, textColor=colors.white, alignment=TA_LEFT,
        ),
        "header_meta": ParagraphStyle(
            "KivuHeaderMeta", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.5,
            leading=10, textColor=colors.HexColor("#D8E9E0"), alignment=TA_LEFT,
        ),
        "eyebrow": ParagraphStyle(
            "KivuEyebrow", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.5,
            leading=9, textColor=PDF_GREEN, alignment=TA_LEFT,
        ),
        "team": ParagraphStyle(
            "KivuTeam", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=14,
            leading=17, textColor=PDF_INK, alignment=TA_CENTER,
        ),
        "team_label": ParagraphStyle(
            "KivuTeamLabel", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=6.8,
            leading=8, textColor=PDF_MUTED, alignment=TA_CENTER,
        ),
        "score": ParagraphStyle(
            "KivuScore", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=25,
            leading=27, textColor=PDF_DARK, alignment=TA_CENTER,
        ),
        "score_meta": ParagraphStyle(
            "KivuScoreMeta", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=6.8,
            leading=8, textColor=PDF_DARK, alignment=TA_CENTER,
        ),
        "section": ParagraphStyle(
            "KivuSection", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=9.5,
            leading=11, textColor=PDF_DARK, alignment=TA_LEFT,
        ),
        "section_count": ParagraphStyle(
            "KivuSectionCount", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.5,
            leading=9, textColor=PDF_MUTED, alignment=TA_RIGHT,
        ),
        "label": ParagraphStyle(
            "KivuLabel", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=6.5,
            leading=8, textColor=PDF_MUTED, alignment=TA_LEFT,
        ),
        "value": ParagraphStyle(
            "KivuValue", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.7,
            leading=11, textColor=PDF_INK, alignment=TA_LEFT,
        ),
        "table_head": ParagraphStyle(
            "KivuTableHead", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=6.5,
            leading=8, textColor=colors.white, alignment=TA_LEFT,
        ),
        "table_cell": ParagraphStyle(
            "KivuTableCell", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.2,
            leading=10, textColor=PDF_INK, alignment=TA_LEFT,
        ),
        "minute": ParagraphStyle(
            "KivuMinute", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8,
            leading=10, textColor=PDF_GREEN, alignment=TA_CENTER,
        ),
        "empty": ParagraphStyle(
            "KivuEmpty", parent=styles["BodyText"], fontName="Helvetica-Oblique", fontSize=8,
            leading=10, textColor=PDF_MUTED, alignment=TA_LEFT,
        ),
        "validation_title": ParagraphStyle(
            "KivuValidationTitle", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8.5,
            leading=10, textColor=PDF_DARK, alignment=TA_LEFT,
        ),
        "validation": ParagraphStyle(
            "KivuValidation", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.2,
            leading=9.5, textColor=PDF_INK, alignment=TA_LEFT,
        ),
        "validation_status": ParagraphStyle(
            "KivuValidationStatus", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7,
            leading=8, textColor=PDF_DARK, alignment=TA_RIGHT,
        ),
        "generic_title": ParagraphStyle(
            "KivuGenericTitle", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14,
            leading=17, textColor=PDF_DARK, alignment=TA_LEFT,
        ),
        "generic_note": ParagraphStyle(
            "KivuGenericNote", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.4,
            leading=9.5, textColor=PDF_MUTED, alignment=TA_LEFT,
        ),
    }


def _pdf_brand_header(title, styles, subtitle="Document officiel de compétition"):
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, Paragraph, Table, TableStyle

    logo_path = _pdf_logo_path()
    if logo_path.is_file():
        try:
            logo = Image(str(logo_path), width=25 * mm, height=25 * mm, kind="proportional")
            logo.hAlign = "CENTER"
        except (OSError, ValueError):
            logo = Paragraph("KIVUFOOT", styles["brand"])
    else:
        logo = Paragraph("KIVUFOOT", styles["brand"])
    right = [
        Paragraph("KIVUFOOT", styles["brand"]),
        Paragraph(escape(title), styles["header_title"]),
        Paragraph(escape(subtitle), styles["header_meta"]),
    ]
    header = Table([[logo, right]], colWidths=[32 * mm, 146 * mm], rowHeights=[30 * mm])
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PDF_DARK),
                ("BOX", (0, 0), (-1, -1), 0.7, PDF_DARK),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return header


def _pdf_section_heading(title, count, styles):
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle

    heading = Table(
        [[Paragraph(escape(title), styles["section"]), Paragraph(escape(count or ""), styles["section_count"])]],
        colWidths=[138 * mm, 40 * mm],
    )
    heading.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PDF_CREAM),
                ("LINEBELOW", (0, 0), (-1, -1), 1.4, PDF_GREEN),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return heading


def _pdf_fact_table(rows, styles, empty_text):
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle

    data = [[
        Paragraph("MINUTE", styles["table_head"]),
        Paragraph("JOUEUR", styles["table_head"]),
        Paragraph("FAIT", styles["table_head"]),
    ]]
    if rows:
        for minute, player, fact in rows:
            data.append([
                Paragraph(escape(_pdf_value(minute)), styles["minute"]),
                _pdf_paragraph(player, styles["table_cell"]),
                _pdf_paragraph(fact, styles["table_cell"]),
            ])
    else:
        data.append([Paragraph(escape(empty_text), styles["empty"]), "", ""])
    table = Table(data, colWidths=[22 * mm, 83 * mm, 73 * mm], repeatRows=1)
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), PDF_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, PDF_LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("SPAN", (0, 1), (-1, 1)) if not rows else ("BACKGROUND", (0, 1), (-1, -1), colors.white),
    ]
    if rows:
        for index in range(2, len(data)):
            if index % 2 == 0:
                commands.append(("BACKGROUND", (0, index), (-1, index), PDF_SOFT))
    table.setStyle(TableStyle(commands))
    return table


def _pdf_info_grid(items, styles):
    from reportlab.lib.units import mm
    from reportlab.platypus import Table, TableStyle

    data = []
    for left_label, left_value, right_label, right_value in items:
        data.append([
            _pdf_paragraph(left_label, styles["label"]),
            _pdf_paragraph(left_value, styles["value"]),
            _pdf_paragraph(right_label, styles["label"]),
            _pdf_paragraph(right_value, styles["value"]),
        ])
    table = Table(data, colWidths=[29 * mm, 60 * mm, 29 * mm, 60 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), PDF_CREAM),
                ("BACKGROUND", (2, 0), (2, -1), PDF_CREAM),
                ("GRID", (0, 0), (-1, -1), 0.35, PDF_LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _pdf_validation_card(styles, status="MATCH VALIDÉ"):
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle

    name, email, phone, whatsapp = _pdf_contact()
    text = (
        "Données issues des éléments officiellement validés par KivuFoot. "
        "L'autorité sportive reste le Comité d'Organisation.<br/>"
        f"Contact : {escape(name)} · {escape(email)} · appels {escape(phone)} · WhatsApp {escape(whatsapp)}"
    )
    card = Table(
        [[Paragraph("VALIDATION OFFICIELLE", styles["validation_title"]), Paragraph(escape(status), styles["validation_status"])],
         [Paragraph(text, styles["validation"]), ""]],
        colWidths=[126 * mm, 52 * mm],
    )
    card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PDF_SOFT),
                ("BOX", (0, 0), (-1, -1), 0.7, PDF_GREEN),
                ("SPAN", (0, 1), (-1, 1)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return card


def _pdf_bytes(title: str, blocks: list[tuple[str, str]]) -> bytes:
    """Document générique brandé pour les fiches joueur et contrôles PDF."""
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Spacer, Table, TableStyle

    _pdf_palette()
    styles = _pdf_styles()
    output = io.BytesIO()
    contact_name, _, phone, whatsapp = _pdf_contact()
    footer_contact = f"{contact_name} · {phone} · WhatsApp {whatsapp}"
    doc = _pdf_document(output, title, footer_contact)
    story = [_pdf_brand_header(title, styles), Spacer(1, 5 * mm)]
    story.append(_pdf_section_heading("INFORMATIONS DU DOCUMENT", "", styles))
    data = [[_pdf_paragraph(key, styles["label"]), _pdf_paragraph(value, styles["value"])] for key, value in blocks]
    table = Table(data, colWidths=[48 * mm, 130 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), PDF_CREAM),
                ("GRID", (0, 0), (-1, -1), 0.35, PDF_LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([table, Spacer(1, 7 * mm), _pdf_validation_card(styles, "DONNÉES VALIDÉES")])
    doc.build(story)
    return output.getvalue()


def _format_match_date(value):
    if value is None:
        return "Non disponible"
    months = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc.")
    return f"{value.day:02d} {months[value.month - 1]} {value.year} · {value:%H:%M}"


def _format_minute(event) -> str:
    if not getattr(event, "minute_connue", True):
        return "—"
    minute = event.minute
    additionnelle = getattr(event, "minute_additionnelle", 0) or 0
    return f"{minute}+{additionnelle}'" if additionnelle else f"{minute}'"


def _match_pdf_bytes(
    *,
    competition: str | None,
    edition: str | None,
    matchday: str | None,
    date_heure,
    stadium: str | None,
    home: str | None,
    away: str | None,
    score_home,
    score_away,
    goals: list[tuple[str, str, str]],
    discipline: list[tuple[str, str, str]],
    man_of_match: str | None,
) -> bytes:
    """Feuille de match A4, lisible à l'écran comme à l'impression."""
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    _pdf_palette()
    styles = _pdf_styles()
    output = io.BytesIO()
    contact_name, _, phone, whatsapp = _pdf_contact()
    doc = _pdf_document(output, "FEUILLE OFFICIELLE DU MATCH", f"{contact_name} · {phone} · WhatsApp {whatsapp}")
    story = [
        _pdf_brand_header("FEUILLE OFFICIELLE DU MATCH", styles, "Résultat, faits de match et validation officielle"),
        Spacer(1, 4 * mm),
    ]

    competition_line = Table(
        [[
            _pdf_paragraph(competition, styles["eyebrow"]),
            _pdf_paragraph(matchday, styles["section_count"]),
        ]],
        colWidths=[138 * mm, 40 * mm],
    )
    competition_line.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 1),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(competition_line)

    score_home_text = "—" if score_home is None else str(score_home)
    score_away_text = "—" if score_away is None else str(score_away)
    score_box = Table(
        [[Paragraph(f"{escape(score_home_text)}  –  {escape(score_away_text)}", styles["score"])],
         [Paragraph("SCORE OFFICIEL", styles["score_meta"])]],
        colWidths=[40 * mm],
    )
    score_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PDF_LIME),
        ("BOX", (0, 0), (-1, -1), 0.8, PDF_GREEN),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    matchup = Table(
        [[
            [Paragraph("DOMICILE", styles["team_label"]), _pdf_paragraph(home, styles["team"])],
            score_box,
            [Paragraph("EXTÉRIEUR", styles["team_label"]), _pdf_paragraph(away, styles["team"])],
        ]],
        colWidths=[69 * mm, 40 * mm, 69 * mm],
    )
    matchup.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PDF_SOFT),
        ("BOX", (0, 0), (-1, -1), 0.7, PDF_LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, PDF_LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([matchup, Spacer(1, 4 * mm)])

    story.append(_pdf_info_grid([
        ("COMPÉTITION", competition, "ÉDITION", edition),
        ("JOURNÉE", matchday, "DATE / HEURE", _format_match_date(date_heure)),
        ("STADE", stadium, "STATUT", "Match validé"),
    ], styles))
    story.append(Spacer(1, 5 * mm))
    story.append(_pdf_section_heading("BUTEURS ET FAITS OFFENSIFS", f"{len(goals)} fait(s)", styles))
    story.append(_pdf_fact_table(goals, styles, "Aucun but ou penalty enregistré."))
    story.append(Spacer(1, 5 * mm))
    story.append(_pdf_section_heading("DISCIPLINE", f"{len(discipline)} sanction(s)", styles))
    story.append(_pdf_fact_table(discipline, styles, "Aucune sanction disciplinaire enregistrée."))
    story.append(Spacer(1, 5 * mm))
    story.append(_pdf_section_heading("HOMME DU MATCH", "DÉSIGNATION OFFICIELLE", styles))
    motm = Table([[Paragraph(escape(_pdf_value(man_of_match or "Non désigné")), styles["team"])]], colWidths=[178 * mm])
    motm.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PDF_SOFT),
        ("BOX", (0, 0), (-1, -1), 0.7, PDF_LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([motm, Spacer(1, 5 * mm), _pdf_validation_card(styles)])
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
    goals = []
    discipline = []
    for event in events:
        event_type = _value(event.type)
        player = players.get(event.joueur_id)
        player_name = player.nom_complet if player else "Joueur non renseigné"
        minute = _format_minute(event)
        if event_type in ("but", "but_contre_son_camp", "penalty"):
            if event_type == "but_contre_son_camp":
                fact = "But contre son camp"
            elif event_type == "penalty":
                result = _value(event.resultat)
                fact = "Penalty marqué" if result == "marque" else "Penalty raté" if result == "rate" else "Penalty"
            else:
                fact = "But"
            goals.append((minute, player_name, fact))
        elif event_type in ("carton_jaune", "carton_rouge"):
            discipline.append((minute, player_name, "Carton jaune" if event_type == "carton_jaune" else "Carton rouge"))
    homme = await db.scalar(select(HommeMatch).where(HommeMatch.match_id == match.id))
    homme_text = "Non désigné"
    if homme:
        homme_player = await db.get(Joueur, homme.joueur_id)
        homme_text = homme_player.nom_complet if homme_player else f"Joueur #{homme.joueur_id}"
    snapshot = {
        "pdf_layout_version": PDF_LAYOUT_VERSION,
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
    data = _match_pdf_bytes(
        competition=competition.nom if competition else None,
        edition=saison.nom if saison else None,
        matchday=match.journee,
        date_heure=match.date_heure,
        stadium=match.stade,
        home=home.nom if home else None,
        away=away.nom if away else None,
        score_home=match.score_domicile,
        score_away=match.score_exterieur,
        goals=goals,
        discipline=discipline,
        man_of_match=homme_text,
    )
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
    stat = await db.scalar(
        select(StatistiqueJoueur).where(
            StatistiqueJoueur.joueur_id == joueur_id,
            StatistiqueJoueur.saison_id == saison_id,
        )
    )
    champs_stats = (
        "matchs_joues",
        "titularisations",
        "minutes_jouees",
        "buts",
        "passes_decisives",
        "cartons_jaunes",
        "cartons_rouges",
    )
    if stat is None:
        # Une fiche sans agrégat confirmé ne doit jamais fabriquer une
        # performance nulle. Les champs sont explicitement indisponibles.
        values = {champ: None for champ in champs_stats}
        statuts = {champ: "NON_DISPONIBLE" for champ in champs_stats}
    else:
        values = {champ: getattr(stat, champ) for champ in champs_stats}
        statuts = {champ: "CONFIRMEE" for champ in champs_stats}
    snapshot = {
        "pdf_layout_version": PDF_LAYOUT_VERSION,
        "joueur_id": joueur_id,
        "joueur_nom": joueur.nom_complet,
        "club_actuel_id": joueur.club_actuel_id,
        "saison_id": saison_id,
        "saison_nom": saison.nom,
        "competition_id": saison.competition_id,
        **values,
        "statuts": statuts,
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
            ("Matchs", values["matchs_joues"]),
            ("Titularisations", values["titularisations"]),
            ("Minutes", values["minutes_jouees"]),
            ("Buts", values["buts"]),
            ("Passes décisives", values["passes_decisives"]),
            ("Cartons jaunes", values["cartons_jaunes"]),
            ("Cartons rouges", values["cartons_rouges"]),
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
