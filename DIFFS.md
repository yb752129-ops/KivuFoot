# Diffs pack-pilote-2 (déployé -> pack)

## frontend-web/index.html
@@ -2,7 +2,7 @@
 <html lang="fr">
   <head>
     <meta charset="UTF-8" />
-    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
+    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover" />
     <meta name="color-scheme" content="light dark" />
     <meta name="theme-color" content="#F3EFE4" />
     <title>KivuFoot — Football local, Sud-Kivu</title>

## frontend-web/src/main.jsx
@@ -14,3 +14,9 @@
     </ThemeProvider>
   </React.StrictMode>
 );
+
+if ("serviceWorker" in navigator) {
+  window.addEventListener("load", () => {
+    navigator.serviceWorker.register("/sw.js").catch(() => {});
+  });
+}

## frontend-web/src/App.jsx
@@ -43,6 +43,7 @@
 import Activation from "./pages/Activation.jsx";
 import { AuthProvider, useAuth } from "./auth.jsx";
 import { isAuthenticated } from "./api.js";
+import Reseau from "./components/Reseau.jsx";
 
 function PorteChargement({ children }) {
   const { loading, error, competitions, reessayer } = useKivu();
@@ -70,6 +71,7 @@
 export default function App() {
   return (
     <AuthProvider>
+      <Reseau />
       <KivuProvider>
         <PorteChargement>
         <Routes>

## frontend-web/src/api.js
@@ -28,11 +28,23 @@
     const t = getToken();
     if (t) headers.Authorization = `Bearer ${t}`;
   }
-  const res = await fetch(`${API}${path}`, {
-    method,
-    headers,
-    body: body !== undefined ? JSON.stringify(body) : undefined,
-  });
+  const ctrl = new AbortController();
+  const timer = setTimeout(() => ctrl.abort(), 12000);
+  let res;
+  try {
+    res = await fetch(`${API}${path}`, {
+      method,
+      headers,
+      body: body !== undefined ? JSON.stringify(body) : undefined,
+      signal: ctrl.signal,
+    });
+  } catch (e) {
+    clearTimeout(timer);
+    const err = new Error("Réseau absent ou trop lent. Vérifiez la connexion, puis réessayez.");
+    err.status = 0;
+    throw err;
+  }
+  clearTimeout(timer);
   if (res.status === 204) return null;
   const text = await res.text();
   let data = null;

## frontend-web/src/styles.css
@@ -2562,3 +2562,33 @@
 .compte-ligne-actions{display:flex;gap:.9rem;align-items:center;flex-shrink:0}
 .avenir-row .btn{width:auto;flex-shrink:0;padding:.55rem .9rem}
 .compte-mdp{margin-top:1.1rem}
+
+/* --- Pack pilote 2 : zoom verrouille + bandeau reseau --- */
+body,
+button,
+a,
+input,
+select,
+textarea {
+  touch-action: manipulation;
+}
+.reseau-perdu {
+  position: fixed;
+  top: 0;
+  left: 0;
+  right: 0;
+  z-index: 90;
+  background: #8c2f2f;
+  color: #f6efe4;
+  font-family: "Source Sans 3", "Segoe UI", sans-serif;
+  font-size: 0.82rem;
+  font-weight: 600;
+  letter-spacing: 0.02em;
+  line-height: 1.35;
+  text-align: center;
+  padding: calc(0.55rem + env(safe-area-inset-top)) 0.9rem 0.55rem;
+}
+html[data-theme="dark"] .reseau-perdu {
+  background: #a03c3c;
+  color: #14120e;
+}

## Fichiers nouveaux
- frontend-web/src/components/Reseau.jsx
- frontend-web/public/sw.js
