# Pack pilote 5 — session partagée survivant à la course de refresh entre onglets

Contenu exact (1 fichier) : frontend-web/src/api.js — seule la fonction refreshSession change :
en cas d'échec du renouvellement, elle relit le refresh token partagé (un autre onglet a pu
le faire pivoter) et réessaie une fois avant de conclure à l'échec. clearTokens ne reste que
pour un échec réel.

Test local (backend réel + deux onglets Playwright, course forcée : onglet 2 envoie son
refresh 900 ms après l'onglet 1 avec la clef déjà lue) :
- SANS correctif : ONGLET 1 /admin, ONGLET 2 /admin, jeton final = STOCKAGE VIDE -> TEST ECHOUE
  (la session commune est vidée : au rendu suivant, /compte partout = symptôme de production).
- AVEC correctif (deux passages) : ONGLET 1 /admin, ONGLET 2 /admin, GET /auth/me = 200
  -> TEST PASSE, les deux onglets restent connectés.

Montage (une seule commande) :
cd ~/kivufoot && tar xzf /sdcard/Download/pack-pilote-5.tgz --strip-components=1 && git add -A && git commit -m "pack-pilote-5 : refresh resistant a la course entre onglets" && git push
