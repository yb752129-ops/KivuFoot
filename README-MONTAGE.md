# Pack pilote 2 — zoom verrouillé, coquille hors ligne, bandeau réseau

Contenu exact (7 fichiers) :
1. frontend-web/index.html — ligne viewport modifiée : zoom pincement et double-tap verrouillés.
2. frontend-web/src/main.jsx — 6 lignes ajoutées : enregistrement du service worker.
3. frontend-web/src/App.jsx — 2 lignes ajoutées : bandeau réseau sur toutes les portes.
4. frontend-web/src/api.js — appel réseau avec temps limite 12 s et message clair si le réseau manque.
5. frontend-web/src/styles.css — lignes ajoutées en fin de fichier : tactile + bandeau.
6. frontend-web/src/components/Reseau.jsx — nouveau : bandeau « Hors connexion ».
7. frontend-web/public/sw.js — nouveau : coquille et polices en cache, API jamais cachée.

Rien d'autre n'est touché. Aucune ligne supprimée hors la ligne viewport remplacée (correctif demandé).

Montage (une seule commande) :
cd ~/kivufoot && tar xzf /sdcard/Download/pack-pilote-2.tgz --strip-components=1 && git add -A && git commit -m "pack-pilote-2 : zoom verrouille, coquille hors ligne, bandeau reseau" && git push
