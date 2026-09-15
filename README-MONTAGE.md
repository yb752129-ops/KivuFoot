# Pack pilote 2 (version 2) — zoom, hors connexion, portes qui restent ouvertes

Contenu exact (7 fichiers) :
1. frontend-web/index.html — ligne viewport modifiée : zoom pincement et double-tap verrouillés.
2. frontend-web/src/main.jsx — 6 lignes ajoutées : enregistrement du service worker.
3. frontend-web/src/App.jsx — 2 lignes ajoutées : bandeau réseau sur toutes les portes.
4. frontend-web/src/api.js — temps limite 12 s + message clair si le réseau manque ;
   renouvellement silencieux de la clef de 30 minutes par la clef de 30 jours (les portes ne renvoient plus à /compte après 30 min).
5. frontend-web/src/styles.css — lignes ajoutées en fin de fichier : tactile + bandeau.
6. frontend-web/src/components/Reseau.jsx — nouveau : bandeau « Hors connexion ».
7. frontend-web/public/sw.js — nouveau : coquille et polices en cache, API jamais cachée.

Rien d'autre n'est touché. Aucune ligne supprimée hors la ligne viewport remplacée (correctif demandé).

Montage (une seule commande) :
cd ~/kivufoot && tar xzf /sdcard/Download/pack-pilote-2.tgz --strip-components=1 && git add -A && git commit -m "pack-pilote-2 : zoom verrouille, hors connexion, portes stables" && git push
