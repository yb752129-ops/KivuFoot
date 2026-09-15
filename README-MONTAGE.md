# Pack pilote 3 — bootstrap du premier admin (une seule fois, audité)

Contenu exact (2 fichiers) :
1. backend/app/main.py — 8 lignes ajoutées en fin de fichier : appel du bootstrap au démarrage.
2. backend/app/auth/bootstrap.py — nouveau : si AUCUN compte staff (admin ou organisateur)
   n'existe au démarrage, le compte yb752129@gmail.com passe admin, et c'est journalisé
   dans la table audit_log. Si un staff existe déjà, ce code ne fait rien, pour toujours.

Aucune donnée n'est touchée d'avance : tout se passe au démarrage de Render, une seule fois.

Montage (une seule commande) :
cd ~/kivufoot && tar xzf /sdcard/Download/pack-pilote-3.tgz --strip-components=1 && git add -A && git commit -m "pack-pilote-3 : bootstrap premier admin audit" && git push

Après le push : attendre environ 2 minutes (Render redémarre), puis se connecter sur
/compte : toutes les portes (/orga, /admin, /collecteur selon rôle, /club, /coach) s'ouvrent.
