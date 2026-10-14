# KivuFoot — rapport de mise en œuvre du 14 octobre 2026

## Résultat

Les corrections ont été préparées dans le checkout `/home/user/kivufoot-merge`.
Aucun push, déploiement ou changement de données de production n'a été effectué.
Les faits historiques n'ont pas été réécrits ni supprimés.

## Publication publique

- `refuse=true` est exclu des événements publics, des statistiques joueur,
  de l'historique joueur, des tops publics, des records et des documents
  nouvellement générés.
- L'historique joueur ne contient un match que lorsqu'il existe une
  participation, un événement `valide` et non refusé, ou une désignation Homme
  du match sur un match officiellement validé.
- Les agrégats historiques ne sont pas utilisés aveuglément pour laisser fuiter
  un événement ensuite refusé : les faits publics sont reconstruits depuis les
  sources officielles filtrées.
- Une participation sans bornes de minutes connues donne `minutes_jouees: null`
  et `participation.minutes: null`. La valeur 90 n'est plus fabriquée dans la
  vue publique.
- Le frontend `frontend-web/src/pages/Joueur.jsx` affiche `Non disponible` pour
  les valeurs nulles et distingue explicitement zéro d'une donnée non collectée.

## Tests ajoutés ou maintenus

Les tests de non-régression couvrent notamment :

- événement refusé absent de la route publique ;
- événement refusé absent des statistiques et du top buteurs ;
- match sans trace joueur absent de l'historique ;
- désignation Homme du match officielle suffisante pour publier une ligne ;
- participation confirmée sans agrégat ;
- minutes inconnues conservées à `null`, sans fabrication de 90 minutes.

Dernier contrôle local : **80 tests backend PostgreSQL passés**.
Le build frontend Vite est également passé.

## Règlement et historique

Le moteur ne crée pas de `ReglementVersion` automatiquement et ne rétro-rattache
pas de règlement aux données historiques. En l'absence de règlement officiel,
les contrôles spécifiques restent non appliqués ou en attention ; aucune règle
sportive nouvelle n'est inventée par cette correction.

## Sauvegardes

- `backend/scripts/backup_postgres.sh` : dump custom, vérification `pg_restore`,
  checksum et rétention locale ;
- `backend/scripts/restore_postgres.sh` : restauration destructive bloquée par
  défaut ;
- procédure détaillée dans `docs/POSTGRES_BACKUP_RUNBOOK.md`.

## PDF et identité confirmée

Le vrai logo complet, et non le simple favicon, est :

- source : `frontend-web/public/icone-512.png` ;
- copie backend : `backend/app/assets/kivufoot-logo.png` ;
- SHA-256 commun :
  `55a5e346d9aea68c01da6ec3cf75aaf4d07be9c8637341442ab430bb87b7eaa0`.

Les coordonnées ont été confirmées dans
`/home/user/KivuFoot_proposition_fiches_performance.pdf`, page 2 :

- Yves Bukasa ;
- `yb752129@gmail.com` ;
- appels `+257 64504091` ;
- WhatsApp `+243 983753771`.

Le générateur PDF utilise ces coordonnées confirmées et affiche
`Non disponible` pour un champ statistique nul côté collecte. Un PDF de contrôle
est disponible ici :

`/home/user/kivufoot-work/controle-pdf-kivufoot-logo-20261014.pdf`

Il contient le logo embarqué, les coordonnées confirmées, `Non disponible` pour
les champs absents et `0` pour une valeur nulle explicite. La checklist de
source est dans `docs/PDF_CONFIRMATION_CHECKLIST.md`.

### Amélioration visuelle préparée après les captures

- `backend/app/services/documents_officiels.py` utilise la mise en page PDF
  version 2 : bandeau KivuFoot avec logo, afficheurs des deux équipes et du
  score, grille compétition/date/stade, sections séparées pour buts et
  discipline, Homme du match, validation officielle et pied de page.
- Les noms longs sont placés dans des cellules avec retour à la ligne ; les
  données absentes restent `Non disponible`, `Aucun ... enregistré` ou
  `Non désigné` selon le champ. Aucune signature, cachet ou validation n'est
  inventé.
- Une nouvelle empreinte de mise en page force la régénération d'une nouvelle
  version d'un ancien PDF sans changer les données historiques.
- Exemple généré :
  `/home/user/kivufoot-work/controle-pdf-kivufoot-match-redesigne-20261014.pdf`.

## Correctifs des captures d'écran

- L'approbation d'une date de naissance convertit maintenant `AAAA-MM-JJ` en
  vraie date avant écriture. Les approbations du nom, du poste et du club sont
  également converties et contrôlées ; un club inexistant ou un poste invalide
  est refusé avec un message explicite, sans erreur SQL générique.
- La page Propositions ne charge plus l'annuaire global plafonné à 100 joueurs
  pour afficher les noms des propositions ; elle charge seulement les profils
  concernés et conserve les propositions visibles si un profil est lent.
- Le compteur Joueurs de la vue organisateur vient maintenant des résumés
  d'effectifs de l'édition et non de `/joueurs?limit=100`. Il ne présente plus
  une limite API comme un total exact ; pendant le chargement, il affiche `—`.
- Le texte « Les 15 clubs » a été remplacé par « Les clubs inscrits » pour ne
  pas contredire une compétition qui en compte 16 ou un autre nombre réel.

## Volet commercial et validation terrain

Un test est en cours à l'Université Espoir d'Afrique, à Bujumbura, dans le
cadre d'un tournoi Interdépartemental. Il s'agit d'une validation réelle et
d'une preuve de progression du produit, pas d'un changement de marché cible.
Les résultats ne doivent être publiés qu'avec des faits vérifiés et les
autorisations nécessaires.

Les livrables sont dans `docs/` :

- `PLAN_COMMERCIAL_30_JOURS.md` : marché cible = Est de la RDC, avec pilote
  initial à Bukavu/Sud-Kivu ; Uvira et les autres villes viennent ensuite ;
  Bujumbura/Burundi ne font pas partie de la prospection cible ;
- `QUESTIONS_TERRAIN.md` : dix questions d'entretien ;
- `OFFRES_COMMERCIALES_HYPOTHESES.md` : trois offres à tester, sans présenter
  de client, revenu, sponsor, audience ou partenaire comme acquis.
