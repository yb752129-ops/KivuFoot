# KivuFoot — Architecture & rapport d'analyse

Ce document rassemble le rapport d'analyse de la spécification originale
(Phase 0) et les décisions d'architecture qui en découlent (Phase 1). Il
sert de référence pour comprendre **pourquoi** le code diffère par endroits
du texte de la spécification initiale — aucune règle métier n'a été
supprimée ou simplifiée sans justification explicite ci-dessous.

## 1. Incohérences bloquantes corrigées

### A1 — `evenements_match` incomplète vis-à-vis de ses propres règles
Le type `remplacement` exigeait `joueur_sortant_id` / `joueur_entrant_id`,
absents du schéma original. Le type `penalty` exigeait un `résultat`,
également absent. Correction :
- `joueur_secondaire_id` (générique) porte la sémantique du passeur
  (`passe_decisive`) ou du joueur entrant (`remplacement`) selon `type`.
- `resultat` (`marque`/`rate`) ajouté, utilisé uniquement pour `penalty`.
- **Règle stricte** : un penalty marqué compte comme un but à part entière
  et n'est **jamais** dupliqué en un second événement `but` — voir
  `app/services/calcul_stats.py`.
- Type `but_contre_son_camp` ajouté (absent de la spec originale) pour ne
  pas créditer le buteur d'un but marqué contre son propre camp.

### A2 — Ambiguïté validation événement vs validation match
La transition `brut → en_attente` n'avait pas de mécanisme déclencheur
explicite. Décision : `brut` est un concept **client uniquement**
(IndexedDB), jamais persisté côté serveur. À réception via `/sync/push` ou
saisie directe, le statut serveur est `en_attente` d'office. La validation
du **match** (verrouillage final, publication) est une action distincte de
l'organisateur (`POST /matchs/{id}/valider`), possible seulement si plus
aucun événement n'est `en_attente`.

### A3 — `locked` absent au niveau événement
Ajouté sur `evenements_match` : un événement validé devient immuable
(`locked=True`), pas seulement le match dans son ensemble.

### A4 — Clé primaire incorrecte sur `statistiques_joueurs`
`joueur_id` seul empêchait des statistiques distinctes par compétition et
saison. Corrigé en clé composite `(joueur_id, competition_id, saison_id)`.

## 2. Tables et colonnes manquantes ajoutées

| Élément | Raison |
|---|---|
| `conflits_synchronisation` | Mentionnée en texte (§6.3 original) mais absente du modèle de données |
| `consentements` | Idem (§10.1 original) |
| `organisateur_competitions` | Sans cette table, la règle RBAC "un organisateur ne valide que ses compétitions" était inapplicable |
| `match_participations` | Aucune table ne permettait de savoir qui a joué, titulaire ou remplaçant — indispensable pour `titularisations`/`minutes_jouees` |
| `refresh_tokens` | Un JWT stateless seul ne peut pas être révoqué au logout |
| `joueurs_modifications_proposees` | Formalise le workflow de proposition du club_manager (décision C1) |
| `joueurs.fusionne`, `fusionne_vers_id`, `statut_verification`, `autorisation_parentale`, `anonymise` | Mentionnés en texte, absents du schéma original |
| `evenements_match.conflit`, `.temp_id`, `.locked`, `.resultat` | Voir A1 et gestion des conflits |
| `matchs.forfait`, `.forfait_equipe` | Un forfait tracé explicitement plutôt qu'un score 3-0 muet (perte de traçabilité sinon) |

## 3. Décisions validées avec le porteur produit (points C1-C5)

- **C1 — Modification de joueur par club_manager** : les champs sensibles
  (`club_actuel_id`, `date_naissance`, `nom_complet`, `poste`) passent par
  un workflow de proposition/approbation (`JoueurModificationProposee`).
  Les champs non sensibles (`telephone`, `email`) sont modifiables
  directement.
- **C2 — Historique des transferts** : les statistiques et l'appartenance
  club-par-match se basent **exclusivement** sur `match_participations`
  (feuille de match), jamais sur `joueurs.club_actuel_id`, qui ne reflète
  que le club *actuel* et fausserait l'histoire après un transfert.
- **C3 — Forfait traçable** : `matchs.forfait` + `forfait_equipe` au lieu
  d'un score 3-0 indiscernable d'un résultat normal.
- **C4 — WebSocket/Redis différés en V1** : `/sync/pull` fonctionne en
  polling. Plus simple et plus robuste sur connexion instable que
  d'ajouter une dépendance temps réel non indispensable au MVP. `REDIS_URL`
  reste configurable pour une réintroduction en V2 sans migration de code.
- **C5 — Cycle de vie du match** : `programme → en_cours → termine →
  valide` (transitions manuelles par l'organisateur), ou `conteste` à tout
  moment. Seule la route dédiée `/matchs/{id}/valider` peut amener un
  match à `valide` (elle seule vérifie qu'aucun événement n'est en
  attente et verrouille le match).

## 4. Règles de fiabilité appliquées dans le code

- **Idempotence de la synchronisation** : chaque événement porte un
  `temp_id` (UUID généré côté client). Un retry réseau ne peut jamais
  dupliquer un événement (`app/services/sync_offline.py`).
- **Immutabilité post-validation** : un événement ou un match validé ne
  peut plus être modifié (`locked=True`), imposé au niveau service ET par
  les contraintes de la base.
- **Audit systématique** : toute validation, rejet, fusion, changement de
  statut passe par `services/audit.py` et alimente `audit_log`
  (old_data/new_data en JSONB), toujours dans la même transaction que
  l'action métier qu'elle documente.
- **Séparation DEMO** : `Competition.est_demo`, préfixe `"DEMO - "`,
  script `scripts/seed_demo.py` idempotent et clairement isolé.
- **RBAC scopé** : middleware centralisé (`app/auth/rbac.py`) vérifiant
  rôle + portée (club pour club_manager, compétitions possédées pour
  organisateur via `organisateur_competitions`).

## 5. Choix techniques

- **SQLAlchemy 2.0** (style `Mapped`/`mapped_column`), async avec
  `asyncpg`.
- **Enums applicatifs** (`app/models/enums.py`) doublés de contraintes
  `CHECK` SQL dans les migrations : la validation existe à deux niveaux
  (application + base), pour que l'intégrité tienne même en cas d'écriture
  directe en base.
- **Alembic** pour toutes les évolutions de schéma — jamais de
  `schema.sql` appliqué manuellement.
- **Pydantic v2** pour la validation des entrées/sorties API, avec
  validation des champs obligatoires par type d'événement
  (`app/schemas/evenement.py`).
- **PWA collecteur** : React + Vite + Service Worker (vite-plugin-pwa) +
  IndexedDB (Dexie). Écriture locale immédiate, synchronisation en
  arrière-plan, jamais de blocage de la saisie par le réseau.

## 6. Limites connues de cette livraison

- Interfaces organisateur et publique (Phases 5-6) non construites dans ce
  ZIP — l'API les supporte déjà entièrement (voir `/docs`).
- Rate limiting sur `/auth/login` configuré mais non branché techniquement
  (à faire avec `slowapi` ou au niveau reverse proxy).
- Sauvegarde automatique PostgreSQL non configurée (à faire au niveau
  infrastructure de déploiement).
- Tests écrits mais non exécutés dans l'environnement de génération de ce
  projet (pas d'accès réseau pour installer les dépendances) — à lancer et
  corriger côté utilisateur avant mise en production.
