# KivuFoot

Infrastructure numérique du football local (Bukavu, Sud-Kivu) : collecte
terrain hors-ligne → validation par l'organisateur → publication publique
(classements, statistiques, profils joueurs), avec traçabilité complète.

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

**Les Phases 5 et 6 ne sont pas dans ce ZIP.** L'API backend expose déjà
tout ce dont elles ont besoin (routes publiques + documentation OpenAPI sur
`/docs`), mais je n'ai pas construit les interfaces web organisateur/public
dans cette passe pour livrer un backend + PWA collecteur réellement complets
et testés plutôt que six interfaces à moitié faites. Dites-moi si vous
voulez que je les construise ensuite.

## ⚠️ Important : les tests n'ont pas été exécutés dans mon environnement

Je n'ai pas d'accès réseau dans le sandbox où j'ai écrit ce code (impossible
d'installer PostgreSQL, FastAPI, pytest, etc.). J'ai donc :
- vérifié la **syntaxe** de chaque fichier Python (`py_compile`) ;
- relu manuellement chaque module pour la cohérence des imports, des types,
  des contraintes ;
- mais je n'ai **pas** lancé `pytest` ni démarré le serveur réellement.

**Avant de considérer ce projet comme fonctionnel, lancez vous-même les
commandes de la section "Lancer les tests" ci-dessous** et corrigez les
éventuelles erreurs d'exécution (typos non détectés par l'analyse statique,
incompatibilités de versions, etc.). Je reste disponible pour déboguer avec
vous à partir des messages d'erreur réels.

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
- [ ] Exécuter réellement la suite de tests et corriger les éventuelles
      erreurs d'exécution non détectables par une simple analyse statique.
- [ ] Configurer la sauvegarde automatique quotidienne de PostgreSQL (§14.5
      de la spécification originale — non implémentée dans ce ZIP).
- [ ] Configurer un vrai pipeline CI/CD (squelette GitHub Actions fourni
      dans `.github/workflows/backend-tests.yml`, à adapter).
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
