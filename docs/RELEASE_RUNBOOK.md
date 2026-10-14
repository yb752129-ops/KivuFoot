# KivuFoot - release professionnelle

## Recommandation

Le chemin recommande est:

1. staging Render avec une base de test ou preproduction isolee;
2. migrations additives et smoke tests sur staging;
3. validation manuelle des routes publiques, du frontend et des PDF;
4. sauvegarde PostgreSQL de production;
5. deploiement production API puis frontend;
6. verification post-deploiement et surveillance;
7. retour arriere uniquement selon le plan valide.

Un deploiement direct en production reste possible, mais il est moins
professionnel car il supprime l'etape de verification dans un environnement
proche de la production.

## Etat de cette release

- Tests backend PostgreSQL: `80 passed` lors du dernier contrôle local.
- Build frontend Vite: réussi lors du dernier contrôle local; le workflow CI
  le rejoue.
- Le vrai logo complet est maintenant embarqué dans
  `backend/app/assets/kivufoot-logo.png`.
- Aucun remote Git n'est configure dans le checkout actuel.
- Aucun secret GitHub, Render, Supabase ou PostgreSQL n'est present dans le
  depot.
- Les donnees historiques ne doivent pas etre modifiees.
- Le logo et les coordonnées PDF sont confirmés dans
  `docs/PDF_CONFIRMATION_CHECKLIST.md`; le PDF de contrôle est
  `kivufoot-work/controle-pdf-kivufoot-logo-20261014.pdf`.

## Pre-deploiement

- [ ] Connecter le depot Git au fournisseur autorise.
- [ ] Verifier le commit de release et la liste des fichiers modifies.
- [ ] Configurer `SECRET_KEY` et `DATABASE_URL` hors du depot.
- [ ] Configurer les URLs CORS de production.
- [ ] Confirmer `SUPABASE_URL` et `SUPABASE_SERVICE_ROLE` si les documents ou
      logos doivent etre stockes.
- [x] Confirmer le logo et les variables `PDF_*` dans
      `docs/PDF_CONFIRMATION_CHECKLIST.md`; vérifier les secrets d'environnement
      avant publication.
- [ ] Faire une sauvegarde PostgreSQL et verifier son checksum.
- [ ] Confirmer la cible exacte et le plan de retour.

## Migrations

L'autorisation actuelle couvre les migrations Alembic additives seulement.
Avant execution:

```bash
alembic upgrade head
```

Verifier la liste des migrations et refuser toute migration qui supprimerait,
viderait ou reecrirait des donnees historiques. Ne jamais lancer une commande
SQL destructive pour "nettoyer" la production.

## Smoke tests apres API

- `GET /health` retourne 200 et `environment=production`.
- Les routes publiques repondent sans authentification.
- Un evenement `refuse=true` n'est pas visible publiquement.
- Un joueur sans participation affiche `Non disponible` dans le frontend.
- Les routes stats et historique repondent pour un joueur connu.
- Les documents PDF ne sont publies que si leur identite est confirmee.
- Les logs ne contiennent aucun secret.

## Frontend

- Verifier la variable `VITE_API_BASE_URL`.
- Verifier la page joueur, l'affichage `Non disponible` et l'historique.
- Verifier les URLs de logo et d'API depuis le navigateur de production.
- Ne pas utiliser `localhost` dans une build publique.

## Retour arriere

- Ne pas restaurer la base automatiquement pour un simple probleme frontend.
- Pour un probleme de code, revenir au commit applicatif precedent si les
  migrations sont compatibles.
- Pour une corruption ou perte de donnees, arreter les ecritures, confirmer la
  cible et utiliser le runbook PostgreSQL avec une autorisation distincte.
- Conserver l'audit et le compte-rendu de l'incident.
