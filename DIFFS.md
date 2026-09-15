# Diffs pack-pilote-5 (déployé -> pack) — UNE SEULE FONCTION : refreshSession

## frontend-web/src/api.js
@@ -24,28 +24,35 @@
 let refreshEnCours = null;
 
 async function refreshSession() {
-  const rf = localStorage.getItem(REFRESH_KEY);
+  let rf = localStorage.getItem(REFRESH_KEY);
   if (!rf) return false;
-  if (!refreshEnCours) {
-    refreshEnCours = (async () => {
-      try {
-        const r = await fetch(`${API}/auth/refresh`, {
-          method: "POST",
-          headers: { "Content-Type": "application/json", Accept: "application/json" },
-          body: JSON.stringify({ refresh_token: rf }),
-        });
-        if (!r.ok) return false;
-        const t = await r.json();
-        setTokens(t.access_token, t.refresh_token);
-        return true;
-      } catch {
-        return false;
-      } finally {
-        refreshEnCours = null;
-      }
-    })();
+  for (let essai = 0; essai < 2; essai++) {
+    if (!refreshEnCours) {
+      refreshEnCours = (async () => {
+        try {
+          const r = await fetch(`${API}/auth/refresh`, {
+            method: "POST",
+            headers: { "Content-Type": "application/json", Accept: "application/json" },
+            body: JSON.stringify({ refresh_token: rf }),
+          });
+          if (!r.ok) return false;
+          const t = await r.json();
+          setTokens(t.access_token, t.refresh_token);
+          return true;
+        } catch {
+          return false;
+        } finally {
+          refreshEnCours = null;
+        }
+      })();
+    }
+    if (await refreshEnCours) return true;
+    // Un autre onglet a peut-etre fait pivoter la clef : relire avant de conclure.
+    const neuf = localStorage.getItem(REFRESH_KEY);
+    if (!neuf || neuf === rf) return false;
+    rf = neuf;
   }
-  return refreshEnCours;
+  return false;
 }
 
 async function request(path, { method = "GET", body, auth = false } = {}, aDejaRetry = false) {
