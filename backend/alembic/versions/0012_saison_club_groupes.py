"""Groupes officiels par inscription saison-club.

Revision ID: 0012_saison_club_groupes
Revises: 0011_activation

Ajouts non destructifs :
- saison_clubs.groupe, nullable pour préserver les anciennes saisons dont le
  groupe ne peut pas être établi avec certitude ;
- contrainte A/B/C/D et index de lecture par saison/groupe ;
- affectation explicite des 15 inscriptions de la saison 2 ;
- reconstruction uniquement certaine pour les anciennes saisons ;
- réalignement de matchs.groupe quand les deux inscriptions portent le même
  groupe officiel.

Aucune équipe, aucun match, aucun utilisateur et aucune donnée existante n'est
supprimé.
"""

from alembic import op
import sqlalchemy as sa

revision = "0012_saison_club_groupes"
down_revision = "0011_activation"
branch_labels = None
depends_on = None

AFFECTATIONS_SAISON_2 = (
    ("G.C.V", "A"),
    ("INFO-2026", "A"),
    ("G.G.T-GRF", "A"),
    ("SANTÉ PUBLIC", "A"),
    ("G.G.T-2025", "B"),
    ("INFO-2024+2025", "B"),
    ("EGA", "B"),
    ("+243(SAE)", "B"),
    ("SIF", "C"),
    ("NUTRITION + OPHTALMOLOGIE", "C"),
    ("LES CHAMPIONS", "C"),
    ("G.G.T-2026", "C"),
    ("DROIT", "D"),
    ("FC ESPOIR", "D"),
    ("ANR", "D"),
)


def _affecter_saison_2(bind) -> None:
    """Affecte uniquement les lignes exactes déjà inscrites en saison 2.

    Une base neuve n'a pas encore de saison 2 : elle passe sans données. Une
    base existante avec une saison 2 incomplète échoue volontairement plutôt
    que d'enregistrer une répartition partielle ou devinée.
    """
    saison_2 = bind.execute(sa.text("SELECT 1 FROM saisons WHERE id = 2 LIMIT 1")).first()
    if saison_2 is None:
        return

    for nom, groupe in AFFECTATIONS_SAISON_2:
        rows = bind.execute(
            sa.text(
                """
                SELECT sc.club_id
                FROM saison_clubs AS sc
                JOIN clubs AS c ON c.id = sc.club_id
                WHERE sc.saison_id = :saison_id AND c.nom = :nom
                """
            ),
            {"saison_id": 2, "nom": nom},
        ).all()
        if len(rows) != 1:
            raise RuntimeError(
                f"Affectation saison 2 impossible pour {nom!r}: {len(rows)} inscription(s) exacte(s)."
            )
        bind.execute(
            sa.text(
                """
                UPDATE saison_clubs
                SET groupe = :groupe
                WHERE saison_id = :saison_id AND club_id = :club_id
                """
            ),
            {"saison_id": 2, "club_id": rows[0][0], "groupe": groupe},
        )


def _reconstruire_anciennes_saisons(bind) -> None:
    """Ne remplit que les cas où tous les matchs donnent un groupe unique."""
    bind.execute(
        sa.text(
            """
            UPDATE saison_clubs AS sc
            SET groupe = groupes_uniques.groupe
            FROM (
                SELECT
                    sc2.saison_id,
                    sc2.club_id,
                    MIN(m.groupe) AS groupe
                FROM saison_clubs AS sc2
                JOIN matchs AS m
                  ON m.saison_id = sc2.saison_id
                 AND (m.equipe_domicile_id = sc2.club_id OR m.equipe_exterieur_id = sc2.club_id)
                GROUP BY sc2.saison_id, sc2.club_id
                HAVING COUNT(*) > 0
                   AND COUNT(m.groupe) = COUNT(*)
                   AND COUNT(DISTINCT m.groupe) = 1
                   AND MIN(m.groupe) IN ('A', 'B', 'C', 'D')
            ) AS groupes_uniques
            WHERE sc.saison_id = groupes_uniques.saison_id
              AND sc.club_id = groupes_uniques.club_id
              AND sc.groupe IS NULL
            """
        )
    )


def _realigner_groupes_matchs(bind) -> None:
    """Aligne les matchs de poule lorsque les deux groupes officiels concordent."""
    bind.execute(
        sa.text(
            """
            UPDATE matchs AS m
            SET groupe = domicile.groupe
            FROM saison_clubs AS domicile
            JOIN saison_clubs AS exterieur
              ON exterieur.saison_id = domicile.saison_id
             AND exterieur.groupe = domicile.groupe
            WHERE m.phase = 'poule'
              AND m.saison_id = domicile.saison_id
              AND m.equipe_domicile_id = domicile.club_id
              AND m.equipe_exterieur_id = exterieur.club_id
              AND domicile.groupe IS NOT NULL
            """
        )
    )


def upgrade() -> None:
    op.add_column("saison_clubs", sa.Column("groupe", sa.String(length=1), nullable=True))
    op.create_check_constraint(
        "ck_saison_clubs_groupe",
        "saison_clubs",
        "groupe IS NULL OR groupe IN ('A','B','C','D')",
    )
    op.create_index(
        "ix_saison_clubs_saison_groupe",
        "saison_clubs",
        ["saison_id", "groupe"],
    )

    bind = op.get_bind()
    _affecter_saison_2(bind)
    _reconstruire_anciennes_saisons(bind)
    _realigner_groupes_matchs(bind)


def downgrade() -> None:
    op.drop_index("ix_saison_clubs_saison_groupe", table_name="saison_clubs")
    op.drop_constraint("ck_saison_clubs_groupe", "saison_clubs", type_="check")
    op.drop_column("saison_clubs", "groupe")
