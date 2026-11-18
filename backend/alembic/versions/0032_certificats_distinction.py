"""Registre des distinctions, sans modifier les tables sportives."""
from alembic import op
import sqlalchemy as sa
revision = '0032_certificats_distinction'
down_revision = '0031_match_troisieme_place'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('certificats_distinction',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(32), nullable=False, unique=True),
        sa.Column('laureat', sa.String(200), nullable=False),
        sa.Column('distinction', sa.String(200), nullable=False),
        sa.Column('equipe', sa.String(200), nullable=False),
        sa.Column('tournoi', sa.String(250), nullable=False),
        sa.Column('organisateur', sa.String(200), nullable=False),
        sa.Column('statut', sa.String(10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("statut IN ('actif','annule')", name='ck_certificats_distinction_statut'))
    if op.get_bind().dialect.name == 'postgresql':
        # Defense in depth: Supabase may grant new public tables and sequences
        # to its API roles by default. The KivuFoot backend uses its own role.
        op.execute('ALTER TABLE public.certificats_distinction ENABLE ROW LEVEL SECURITY')
        op.execute('REVOKE ALL ON TABLE public.certificats_distinction FROM PUBLIC')
        op.execute('REVOKE ALL ON SEQUENCE public.certificats_distinction_id_seq FROM PUBLIC')
        op.execute("""DO $$
        DECLARE api_role text;
        BEGIN
            FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated'] LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
                    EXECUTE format('REVOKE ALL ON TABLE public.certificats_distinction FROM %I', api_role);
                    EXECUTE format('REVOKE ALL ON SEQUENCE public.certificats_distinction_id_seq FROM %I', api_role);
                END IF;
            END LOOP;
        END $$""")

def downgrade():
    # Interdire la perte des distinctions enregistrées et de leurs liens QR.
    if op.get_bind().execute(sa.text('SELECT COUNT(*) FROM certificats_distinction')).scalar_one():
        raise RuntimeError('Impossible de supprimer le registre non vide.')
    op.drop_table('certificats_distinction')
