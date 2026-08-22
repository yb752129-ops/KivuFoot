-- ============================================================
-- KIVUFOOT — Schéma de base de données (Supabase / PostgreSQL)
-- Principe: chaque donnée sensible porte statut + source + historique
-- ============================================================

create extension if not exists "uuid-ossp";

-- ---------- CHAMPIONNATS / SAISONS / JOURNÉES ----------

create table championnats (
  id uuid primary key default uuid_generate_v4(),
  nom text not null,
  ville text not null default 'Uvira',
  created_at timestamptz not null default now()
);

create table saisons (
  id uuid primary key default uuid_generate_v4(),
  championnat_id uuid not null references championnats(id) on delete cascade,
  libelle text not null, -- ex: "Saison 2026"
  date_debut date,
  date_fin date,
  couverture_depuis date, -- date à partir de laquelle KivuFoot couvre la saison
  active boolean not null default true
);

create table journees (
  id uuid primary key default uuid_generate_v4(),
  saison_id uuid not null references saisons(id) on delete cascade,
  numero int not null,
  date_prevue date
);

-- ---------- CLUBS ----------

create table clubs (
  id uuid primary key default uuid_generate_v4(),
  nom text not null,
  quartier text,
  logo_url text,
  created_at timestamptz not null default now()
);

-- ---------- CORRESPONDANTS ----------

create table correspondants (
  id uuid primary key default uuid_generate_v4(),
  nom text not null,
  telephone text,
  club_id uuid references clubs(id) on delete set null,
  role text not null default 'correspondant', -- correspondant | remplacant | admin
  statut text not null default 'actif', -- actif | inactif
  created_at timestamptz not null default now()
);

-- ---------- JOUEURS ----------

create table joueurs (
  id uuid primary key default uuid_generate_v4(),
  nom text not null,
  club_id uuid references clubs(id) on delete set null,
  position text, -- ex: milieu offensif
  numero int,
  date_naissance date,
  created_at timestamptz not null default now()
);

-- ---------- MATCHS ----------

create table matchs (
  id uuid primary key default uuid_generate_v4(),
  journee_id uuid not null references journees(id) on delete cascade,
  club_domicile_id uuid not null references clubs(id),
  club_exterieur_id uuid not null references clubs(id),
  stade text,
  date_heure timestamptz,
  statut text not null default 'a_venir',
  -- a_venir | live | mi_temps | termine | reporte | annule | abandonne
  score_domicile int default 0,
  score_exterieur int default 0,
  score_statut text not null default 'en_attente',
  -- en_attente | vérifié | en_vérification | contesté
  correspondant_domicile_id uuid references correspondants(id),
  correspondant_exterieur_id uuid references correspondants(id),
  derniere_maj timestamptz,
  created_at timestamptz not null default now()
);

-- ---------- ÉVÉNEMENTS (but, carton, remplacement) ----------

create table evenements (
  id uuid primary key default uuid_generate_v4(),
  match_id uuid not null references matchs(id) on delete cascade,
  type text not null, -- but | carton_jaune | carton_rouge | remplacement | debut | mi_temps | reprise | fin
  minute int,
  club_id uuid references clubs(id),
  joueur_id uuid references joueurs(id),
  joueur_sortant_id uuid references joueurs(id), -- pour remplacement
  joueur_entrant_id uuid references joueurs(id), -- pour remplacement
  note text,

  -- traçabilité obligatoire
  correspondant_id uuid not null references correspondants(id),
  statut text not null default 'en_attente',
  -- en_attente | vérifié | en_vérification | contesté
  soumis_le timestamptz not null default now(),
  modifie_le timestamptz,
  historique jsonb not null default '[]'::jsonb,

  -- lien vers l'événement correspondant soumis par l'autre correspondant (recoupement)
  evenement_concordant_id uuid references evenements(id)
);

create index idx_evenements_match on evenements(match_id);
create index idx_evenements_statut on evenements(statut);

-- ---------- VUE: CLASSEMENT AUTOMATIQUE ----------

create or replace view classement as
select
  c.id as club_id,
  c.nom as club_nom,
  j.saison_id,
  count(*) filter (where m.statut = 'termine') as matchs_joues,
  count(*) filter (
    where m.statut = 'termine' and (
      (m.club_domicile_id = c.id and m.score_domicile > m.score_exterieur) or
      (m.club_exterieur_id = c.id and m.score_exterieur > m.score_domicile)
    )
  ) as victoires,
  count(*) filter (
    where m.statut = 'termine' and m.score_domicile = m.score_exterieur
  ) as nuls,
  count(*) filter (
    where m.statut = 'termine' and (
      (m.club_domicile_id = c.id and m.score_domicile < m.score_exterieur) or
      (m.club_exterieur_id = c.id and m.score_exterieur < m.score_domicile)
    )
  ) as defaites,
  sum(case when m.club_domicile_id = c.id then m.score_domicile
           when m.club_exterieur_id = c.id then m.score_exterieur else 0 end) as buts_marques,
  sum(case when m.club_domicile_id = c.id then m.score_exterieur
           when m.club_exterieur_id = c.id then m.score_domicile else 0 end) as buts_encaisses
from clubs c
join matchs m on m.club_domicile_id = c.id or m.club_exterieur_id = c.id
join journees j on j.id = m.journee_id
where m.score_statut = 'vérifié'
group by c.id, c.nom, j.saison_id;

-- ---------- FONCTION: recoupement automatique ----------
-- Quand deux correspondants soumettent un événement concordant (même type, minute proche, même club),
-- passer les deux à statut 'vérifié'. Logique applicative recommandée côté backend/Edge Function
-- plutôt que trigger pur SQL, car la comparaison "minute proche" demande une tolérance (+/- 1 min).

-- ---------- RLS (Row Level Security) — à activer en prod ----------
alter table evenements enable row level security;
alter table matchs enable row level security;

-- Un correspondant ne peut insérer des événements que pour un match où il est assigné
create policy "correspondant_insert_own_match"
  on evenements for insert
  with check (
    correspondant_id in (
      select id from correspondants where id = correspondant_id
    )
  );

-- Lecture publique des données vérifiées uniquement (le reste réservé à l'admin)
create policy "lecture_publique_verifiee"
  on evenements for select
  using (statut = 'vérifié' or auth.role() = 'authenticated');
