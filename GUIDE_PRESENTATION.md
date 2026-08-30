# KivuFoot — prêt à montrer (prototype)

## Design retenu

Tes captures Posthumain / MTL Connecte sont des **pubs**, pas un produit football.
On a pris le **login sombre + verre + or/vert** (écran Welcome Back) :

- fond nuit (match en soirée)
- vert terrain
- cartes verre
- pas de Google/GitHub (on n’a pas ces connexions)

Le collecteur terrain reste simple et vert clair (saisie au soleil, hors-ligne).

## Ce qui a été ajouté

- `frontend-web/` : site public + espace organisateur
- `GET /api/v1/matchs/gestion` : liste tous les matchs (organisateur)
- seed DEMO enrichi : 4 clubs, 6 matchs **publiés**, 1 match à valider, 1 match à venir
- `SEED_DEMO=true` au démarrage de l’API pour charger la démo

## Comptes démo (après seed)

Mot de passe : `ChangeMoiEnDemo123!`

- Organisateur : `orga.demo@example.com`
- Collecteur : `collecteur.demo@example.com`

## Déploiement (après push GitHub)

1. Variable API : `SEED_DEMO=true` (une fois), puis redéployer
2. CORS : ajouter l’URL du nouveau site
3. Static Site Render, root `frontend-web`
