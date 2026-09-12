"""Activation des comptes créés par l'admin et réinitialisation de mot de passe.

Revision ID: 0011_activation
Revises: 0010_numero

Ajouts non destructifs (aucune donnée existante modifiée) :
- users.jeton_activation_hash : SHA-256 du code d'activation à usage unique
  (le code lui-même n'est JAMAIS stocké, seulement son hash) ;
- users.jeton_activation_expire : échéance du code.

Aucun mot de passe n'est stocké ni migré ici : l'utilisateur choisit le sien
via POST /auth/activation, qui n'écrit que mot_de_passe_hash (bcrypt).
"""

from alembic import op
import sqlalchemy as sa

revision = "0011_activation"
down_revision = "0010_numero"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("jeton_activation_hash", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("jeton_activation_expire", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "jeton_activation_expire")
    op.drop_column("users", "jeton_activation_hash")
