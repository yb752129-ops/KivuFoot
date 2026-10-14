# KivuFoot

Infrastructure numérique du football local (Bukavu, Sud-Kivu) : collecte
terrain hors-ligne → validation par l'organisateur → publication publique
(classements, statistiques, profils joueurs), avec traçabilité complète.

Le marché de départ visé est Bukavu, au Sud-Kivu, puis l'Est de la RDC. Un
test réel est en cours à l'Université Espoir d'Afrique, à Bujumbura, lors d'un
tournoi Interdépartemental : c'est une validation terrain et une preuve de
progression, pas le marché commercial cible de KivuFoot.

> **La fiabilité des données est le seul actif du projet.** Toute décision
> technique de ce dépôt (voir `ARCHITECTURE.md`) a été prise pour préserver
> cette fiabilité, la sécurité, la traçabilité et le fonctionnement
> offline-first — jamais pour aller plus vite.

## État du projet à la livraison de ce ZIP

Ce dépôt couvre les phases suivantes de la méthode de développement convenue :

| Phase | Contenu | État |
|---|---|---|
| 0 | Analyse de la spécification, corrections proposées | ✅ Fait (voir `ARCHITECTURE.md`) |
| 1 | Architecture finale | ✅ Fait |
| 2 | Base de données (modèles, migrations, contraintes, DEMO) | ✅ Fait |
| 3 | Backend (auth, RBAC, matchs, événements, validation, classement, stats, audit, sync) | ✅ Fait |
| 4 | PWA collecteur (offline-first, IndexedDB, synchronisation) | ✅ Fait |
| 5 | Interface organisateur (tableau de bord de validation) | ⏳ Non incluse dans ce ZIP |
| 6 | Interface publique (résultats, classements, fiches joueurs) | ⏳ Non incluse dans ce ZIP |
| 7 | Tests | ✅ Tests unitaires/intégration sur les règles métier critiques (voir `backend/tests/`) |
| 8 | Production (Docker, CI/CD, sauvegardes) | ⚠️ Docker/Compose fournis ; CI/CD et sauvegardes automatiques à configurer sur votre infrastructure (squelette dans `.github/workflows/`) |

Les interfaces publiques et organisateur sont présentes dans
`frontend-web/`; la PWA de collecte reste dans `frontend-collecteur/`. Les
routes publiques et la documentation OpenAPI sont exposées par le backend.

## Contrôles locaux du 14 octobre 2026

- Backend PostgreSQL : `80 passed` avec `pytest`.
- Frontend public : `npm run build` réussi avec Vite.
- Aucun déploiement, push ou modification de données de production n'a été
  effectué depuis ce workspace.
- Le vrai logo complet et les coordonnées PDF sont confirmés dans
  `docs/PDF_CONFIRMATION_CHECKLIST.md`; le logo est embarqué dans
  `backend/app/assets/kivufoot-logo.png`.

## Architecture

Voir `ARCHITECTURE.md` pour : le rapport d'analyse de la spécification
originale, les corrections apportées, et les décisions d'architecture.

```
kivufoot/
├── backend/                 # API FastAPI + PostgreSQL
│   ├── app/
│   │   ├── models/          # SQLAlchemy ORM
│   │   ├── schemas/         # Pydantic
│   │   ├── auth/            # JWT, hashing, RBAC
│   │   ├── routes/          # Endpoints API
│   │   ├── services/        # Logique métier (classement, validation, sync...)
│   │   ├── middlewares/
│   │   └── main.py
│   ├── alembic/              # Migrations de base de données
│   ├── scripts/seed_demo.py  # Données DEMO (séparées, idempotent)
│   ├── tests/                 # pytest
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend-collecteur/      # PWA offline-first (React + Vite + Dexie)
│   ├── src/
│   ├── Dockerfile
│   └── .env.example
├── docker-compose.yml
└── ARCHITECTURE.md
```

## Prérequis

- Docker et Docker Compose (recommandé - tout tourne en conteneurs)
- OU, en local : Python 3.12+, Node.js 20+, PostgreSQL 16+

## Installation et lancement (avec Docker — recommandé)

```bash
git clone <votre-depot>
cd kivufoot

# 1. Configurer les variables d'environnement
cp backend/.env.example backend/.env
# Éditez backend/.env : générez au minimum une vraie SECRET_KEY avec :
openssl rand -hex 32
cp frontend-collecteur/.env.example frontend-collecteur/.env

# 2. Démarrer tous les services (API + PostgreSQL + Adminer + PWA)
docker compose up --build

# 3. Dans un autre terminal : appliquer les migrations (si pas déjà fait au démarrage de l'API)
docker compose exec api alembic upgrade head

# 4. Charger les données de démonstration (optionnel, clairement séparées)
docker compose exec api python -m scripts.seed_demo
```

Services disponibles :
- API : http://localhost:8000 — documentation interactive : http://localhost:8000/docs
- PWA collecteur : http://localhost:5173
- Adminer (interface DB) : http://localhost:8080 (serveur `db`, user/password du `.env`)

## Installation en local (sans Docker, ex. Termux)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env
# éditez .env : DATABASE_URL doit pointer vers un PostgreSQL accessible,
# et SECRET_KEY doit être une vraie valeur aléatoire (openssl rand -hex 32)

alembic upgrade head
python -m scripts.seed_demo   # optionnel
uvicorn app.main:app --reload
```

```bash
cd frontend-collecteur
npm install
cp .env.example .env
npm run dev
```

## Lancer les tests

Les tests nécessitent un **vrai PostgreSQL** dédié aux tests (les modèles
utilisent des colonnes JSONB et des contraintes CHECK spécifiques à
PostgreSQL — un SQLite de secours donnerait de faux positifs sur la
fiabilité, ce qui va à l'encontre de la priorité n°1 du projet).

```bash
# Démarrer uniquement la base de test (isolée de la base de dev)
docker compose up -d db_test

cd backend
source .venv/bin/activate   # si vous n'êtes pas déjà dans l'environnement
pip install -r requirements-dev.txt

pytest                        # tous les tests
pytest --cov=app --cov-report=term-missing   # avec couverture
pytest tests/test_validation_workflow.py -v  # un fichier précis
```

Les tests couvrent notamment :
- le calcul du classement (points, tri, forfait) ;
- le workflow de validation (verrouillage, immutabilité post-validation) ;
- les règles penalty / but contre son camp (pas de double comptage) ;
- l'idempotence de la synchronisation offline (`temp_id`) ;
- la détection de conflits entre deux collecteurs ;
- le RBAC (scope club_manager / organisateur) ;
- la fusion de joueurs ;
- la séparation stricte des données DEMO ;
- l'authentification et la révocation de session.

## Variables d'environnement (backend/.env)

| Variable | Description | Obligatoire |
|---|---|---|
| `DATABASE_URL` | URL PostgreSQL async (`postgresql+asyncpg://...`) | Oui |
| `SECRET_KEY` | Clé secrète JWT — générer avec `openssl rand -hex 32` | Oui |
| `ALGORITHM` | Algorithme JWT (défaut `HS256`) | Non |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée de vie de l'access token (défaut 30) | Non |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Durée de vie du refresh token (défaut 30) | Non |
| `CORS_ALLOW_ORIGINS` | Origines autorisées, séparées par des virgules | Non |
| `S3_*` | Stockage des logos clubs (optionnel V1) | Non |
| `REDIS_URL` | **Volontairement différé en V1** (voir ARCHITECTURE.md) — laisser vide | Non |

Voir `backend/.env.example` pour la liste complète et des exemples.

## Points restant à configurer avant la production

- [ ] Générer une vraie `SECRET_KEY` (jamais celle d'exemple).
- [ ] Configurer un vrai mot de passe PostgreSQL (jamais `changeme`).
- [ ] Construire les interfaces organisateur et publique (Phases 5-6).
- [x] Exécuter la suite backend PostgreSQL : `80 passed` lors du contrôle local
      du 14 octobre 2026.
- [x] Préparer les scripts et le runbook de sauvegarde PostgreSQL
      (`docs/POSTGRES_BACKUP_RUNBOOK.md`); la planification et le stockage
      hors site restent à valider avec l'opérateur.
- [x] Configurer le workflow GitHub Actions backend + build frontend dans
      `.github/workflows/backend-tests.yml`; les secrets de déploiement restent
      volontairement non configurés.
- [ ] Décider d'un mécanisme de rate limiting réel sur `/auth/login` (la
      configuration existe, l'implémentation technique — ex. `slowapi` ou
      un reverse proxy — reste à brancher).
- [ ] Revoir les CORS en production (`CORS_ALLOW_ORIGINS`).

## Licence des données de démonstration

Toutes les données DEMO sont fictives (`DEMO - Championnat de test`, clubs
`DEMO FC Alpha` / `DEMO FC Beta`, joueurs `Joueur Démo A1`, etc.). Aucun nom
de compétition, club ou joueur réel n'a été inventé, conformément à la
règle de la spécification. Supprimez-les avant la mise en production via :

```sql
DELETE FROM competitions WHERE est_demo = TRUE;  -- cascade sur saisons/matchs/etc.
```
