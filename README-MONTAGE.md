# Pack pilote-1 — comptes réels, composition coach, nettoyage démo

Base : ton dépôt exact du 12 septembre (kf-src.txt). Rien d'autre n'est touché.
Contenu : 19 fichiers modifiés ou nouveaux + 1 fichier à supprimer + DIFFS.md (tout le détail ligne par ligne).

## Le geste unique (Termux, après avoir téléchargé le tgz dans Download)

```
cd ~/kivufoot && tar xzf /sdcard/Download/pack-pilote-1.tgz --strip-components=1 && rm frontend-web/src/components/ComptesTest.jsx && git add -A && git commit -m "pack-pilote-1 : comptes reels, composition coach, nettoyage demo" && git push
```

## Ce que fait le paquet

1. Comptes : page /admin/comptes (création coach/club/collecteur/orga, code d'activation
   montré une seule fois, réinitialisation, activer/désactiver), page publique /activation,
   changement de mot de passe dans /compte. Nouveau fichier backend routes/utilisateurs.py,
   routes auth /activation et /changer-mot-de-passe, migration 0011 (2 colonnes, non destructive).
2. Composition coach : /coach/matchs/:id → bouton « Composition » → même éditeur que le club
   (aucune deuxième logique). Verrou renforcé : en_cours, termine, valide.
3. Nettoyage : route purge-demo supprimée du backend, paramètre inclure_demo supprimé
   (frontend + backend), carte « Comptes de test » supprimée (Login + fichier ComptesTest.jsx),
   mots de passe démo retirés de portes.js.

## Après le push

- Render déploie les deux services ; la migration 0011 passe au démarrage comme les 0009/0010.
- Je vérifie moi-même en ligne (openapi, bundle, parcours) dès que tu me dis « poussé ».
- Si Render signalait une colonne manquante (improbable), dis-le-moi : je te donne la commande exacte.
- Aucune variable Render à toucher : PURGE_DEMO_CLE et SEED_DEMO sont déjà retirées.
