# Diffs pack-pilote-3 (déployé -> pack)

## backend/app/main.py (ajout en fin de fichier, aucune ligne supprimée)
@@ -66,3 +66,13 @@
 @app.api_route("/health", methods=["GET", "HEAD"], tags=["Santé"])
 async def health_check():
     return {"status": "ok", "environment": settings.environment}
+
+
+# Bootstrap du premier admin (pack-pilote-3) : une seule fois, uniquement
+# si aucun compte staff n'existe, et journalisé dans la table d'audit.
+from app.auth.bootstrap import bootstrap_premier_admin
+
+
+@app.on_event("startup")
+async def _bootstrap_premier_admin() -> None:
+    await bootstrap_premier_admin()

## Fichiers nouveaux
- backend/app/auth/bootstrap.py
