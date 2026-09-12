# DIFFS — pack-pilote-1 (base = ton dépôt du 12 sept, kf-src.txt)


## backend/app/models/user.py
```diff
@@ -20,6 +20,11 @@
     # club_id : club_manager (effectif) et coach (composition)
     club_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id", ondelete="SET NULL"))
     est_actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
+    # Première activation / réinitialisation du mot de passe : code à usage
+    # unique, stocké UNIQUEMENT haché (SHA-256), montré une seule fois à
+    # l'admin qui le transmet hors écran. Aucun mot de passe n'est stocké ici.
+    jeton_activation_hash: Mapped[str | None] = mapped_column(String(255))
+    jeton_activation_expire: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
     created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
 
     club = relationship("Club", back_populates="managers")
```

## backend/app/schemas/auth.py
```diff
@@ -49,3 +49,61 @@
         if len(nom) < 2:
             raise ValueError("Le nom complet est trop court.")
         return nom
+
+
+# ---------------------------------------------------------------------------
+# Comptes réels : activation, changement de mot de passe, gestion admin.
+# Aucun schéma ne transporte jamais un mot de passe existant vers le client :
+# le hash reste en base, les codes d'activation ne sont montrés qu'une fois.
+# ---------------------------------------------------------------------------
+
+class ActivationRequest(BaseModel):
+    email: EmailStr
+    jeton: str = Field(min_length=10, max_length=120)
+    mot_de_passe: str = Field(min_length=8, max_length=72)
+
+
+class ChangerMotDePasseRequest(BaseModel):
+    mot_de_passe_actuel: str = Field(min_length=1, max_length=72)
+    nouveau_mot_de_passe: str = Field(min_length=8, max_length=72)
+
+
+class AdminUserCreate(BaseModel):
+    nom_complet: str = Field(min_length=2, max_length=255)
+    email: EmailStr
+    role: RoleUtilisateur
+    club_id: int | None = None
+
+    @field_validator("nom_complet")
+    @classmethod
+    def nom_non_vide(cls, v: str) -> str:
+        nom = v.strip()
+        if len(nom) < 2:
+            raise ValueError("Le nom complet est trop court.")
+        return nom
+
+
+class AdminUserUpdate(BaseModel):
+    nom_complet: str | None = Field(default=None, min_length=2, max_length=255)
+    role: RoleUtilisateur | None = None
+    club_id: int | None = None
+    est_actif: bool | None = None
+
+
+class AdminUserOut(BaseModel):
+    model_config = ConfigDict(from_attributes=True)
+
+    id: int
+    email: EmailStr
+    role: RoleUtilisateur
+    nom_complet: str | None
+    club_id: int | None
+    est_actif: bool
+    activation_en_attente: bool = False
+
+
+class CreationCompteOut(BaseModel):
+    utilisateur: AdminUserOut
+    # Code à usage unique, montré UNE seule fois. Ce n'est pas un mot de
+    # passe : l'utilisateur choisit son propre mot de passe à l'activation.
+    jeton_activation: str
```

## backend/app/routes/auth.py
```diff
@@ -1,3 +1,5 @@
+import hashlib
+import secrets
 from datetime import datetime, timedelta, timezone
 
 from fastapi import APIRouter, Depends, HTTPException, status
@@ -9,9 +11,18 @@
 from app.auth.jwt import create_access_token, create_refresh_token_raw, hash_refresh_token
 from app.config import settings
 from app.database import get_db
-from app.models.enums import RoleUtilisateur
+from app.models.enums import ActionAudit, RoleUtilisateur
 from app.models.user import RefreshToken, User
-from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserOut
+from app.schemas.auth import (
+    ActivationRequest,
+    ChangerMotDePasseRequest,
+    LoginRequest,
+    RefreshRequest,
+    RegisterRequest,
+    TokenResponse,
+    UserOut,
+)
+from app.services.audit import log_audit
 
 router = APIRouter(prefix="/auth", tags=["Authentification"])
 
@@ -105,3 +116,87 @@
 @router.get("/me", response_model=UserOut)
 async def me(current_user: User = Depends(get_current_user)):
     return current_user
+
+
+# ---------------------------------------------------------------------------
+# Activation et mot de passe (comptes réels du championnat).
+#
+# Règles non négociables :
+# - l'admin ne choisit, ne voit et ne reçoit JAMAIS un mot de passe ;
+# - le code d'activation n'est stocké que haché (SHA-256), à usage unique ;
+# - chaque changement de mot de passe révoque toutes les sessions (refresh).
+# ---------------------------------------------------------------------------
+
+ACTIVATION_HEURES = 72
+
+
+def _hash_jeton(raw: str) -> str:
+    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
+
+
+def _nouveau_jeton_activation() -> tuple[str, str, datetime]:
+    """Génère (code_brut, hash_sha256, échéance). Le brut n'est jamais stocké."""
+    raw = secrets.token_urlsafe(24)
+    echeance = datetime.now(timezone.utc) + timedelta(hours=ACTIVATION_HEURES)
+    return raw, _hash_jeton(raw), echeance
+
+
+async def _revoquer_sessions(db: AsyncSession, user_id: int) -> None:
+    result = await db.execute(
+        select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
+    )
+    for token in result.scalars().all():
+        token.revoked = True
+
+
+@router.post("/activation", response_model=TokenResponse)
+async def activation(payload: ActivationRequest, db: AsyncSession = Depends(get_db)):
+    """Première connexion d'un compte créé par l'admin : l'utilisateur
+    échange son code à usage unique contre SON propre mot de passe."""
+    user_result = await db.execute(select(User).where(User.email == str(payload.email).lower()))
+    user = user_result.scalar_one_or_none()
+    erreur_code = HTTPException(
+        status.HTTP_401_UNAUTHORIZED, "Code d'activation invalide ou expiré."
+    )
+    if user is None or not user.jeton_activation_hash or not user.jeton_activation_expire:
+        raise erreur_code
+    if user.jeton_activation_expire < datetime.now(timezone.utc):
+        user.jeton_activation_hash = None
+        user.jeton_activation_expire = None
+        await db.commit()
+        raise erreur_code
+    if not secrets.compare_digest(_hash_jeton(payload.jeton), user.jeton_activation_hash):
+        raise erreur_code
+
+    user.mot_de_passe_hash = hash_password(payload.mot_de_passe)
+    user.jeton_activation_hash = None
+    user.jeton_activation_expire = None
+    user.est_actif = True
+    await _revoquer_sessions(db, user.id)
+    await log_audit(
+        db, "users", user.id, ActionAudit.UPDATE, None,
+        {"etat": "activation_en_attente"},
+        {"etat": "actif", "mot_de_passe": "choisi par l'utilisateur"},
+    )
+    await db.flush()
+    return await _issue_tokens(db, user)
+
+
+@router.post("/changer-mot-de-passe", status_code=status.HTTP_204_NO_CONTENT)
+async def changer_mot_de_passe(
+    payload: ChangerMotDePasseRequest,
+    current_user: User = Depends(get_current_user),
+    db: AsyncSession = Depends(get_db),
+):
+    """L'utilisateur connecté change SON propre mot de passe. Personne
+    d'autre : la route n'accepte aucun identifiant tiers."""
+    if not verify_password(payload.mot_de_passe_actuel, current_user.mot_de_passe_hash):
+        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mot de passe actuel incorrect.")
+    current_user.mot_de_passe_hash = hash_password(payload.nouveau_mot_de_passe)
+    await _revoquer_sessions(db, current_user.id)
+    await log_audit(
+        db, "users", current_user.id, ActionAudit.UPDATE, current_user.id,
+        None, {"mot_de_passe": "changé par l'utilisateur"},
+    )
+    await db.commit()
+    return None
```

## backend/app/routes/utilisateurs.py
```diff
(fichier NOUVEAU — absent de ta base)
+ (voir le fichier joint dans le paquet)
```

## backend/app/routes/clubs.py
```diff
@@ -1,9 +1,4 @@
 from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
-import os
-from pydantic import BaseModel
-from app.models.joueur import Joueur
-from app.models.competition import OrganisateurCompetition
-from app.services import stockage_logo, stockage_photo
 from sqlalchemy import or_, select
 from sqlalchemy.ext.asyncio import AsyncSession
 
@@ -342,96 +337,3 @@
                     {"nom_complet": membre.nom_complet, "role": getattr(membre.role, "value", membre.role)}, None)
     await db.delete(membre)
     await db.commit()
-
-
-class PurgeDemoIn(BaseModel):
-    cle: str
-
-
-@router.post("/purge-demo")
-async def purge_demo(payload: PurgeDemoIn, db: AsyncSession = Depends(get_db)):
-    """Operation UNIQUE : efface clubs DEMO, users @example.com et leurs objets.
-    Double verrou : variable Render PURGE_DEMO_CLE + cle exacte dans le corps.
-    Sans la variable, la route repond 404 : elle est morte."""
-    cle_attendue = os.getenv("PURGE_DEMO_CLE", "")
-    if not cle_attendue or payload.cle != cle_attendue:
-        raise HTTPException(status.HTTP_404_NOT_FOUND, "Introuvable.")
-    sup_photo = getattr(stockage_photo, "supprimer_objet", None)
-    rapport = {"objets_photos": 0, "objets_logos": 0, "photos": 0, "matchs": 0,
-               "joueurs": 0, "staffs": 0, "clubs": 0, "users": 0}
-    etape = "debut"
-    try:
-        etape = "lecture_clubs"
-        clubs_demo = (await db.execute(select(Club).where(Club.nom.like("DEMO %")))).scalars().all()
-        club_ids = [c.id for c in clubs_demo]
-        etape = "lecture_users"
-        users_demo = (await db.execute(select(User).where(User.email.like("%@example.com")))).scalars().all()
-        if club_ids:
-            etape = "joueurs_staff"
-            joueurs = (await db.execute(select(Joueur).where(Joueur.club_actuel_id.in_(club_ids)))).scalars().all()
-            joueur_ids = [j.id for j in joueurs]
-            staffs = (await db.execute(select(Staff).where(Staff.club_id.in_(club_ids)))).scalars().all()
-            staff_ids = [m.id for m in staffs]
-            etape = "matchs"
-            matchs = (await db.execute(
-                select(Match).where(or_(Match.equipe_domicile_id.in_(club_ids), Match.equipe_exterieur_id.in_(club_ids)))
-            )).scalars().all()
-            for m in matchs:
-                await db.delete(m)
-            rapport["matchs"] = len(matchs)
-            etape = "photos"
-            conds = []
-            if joueur_ids:
-                conds.append((Photo.sujet_type == "joueur") & Photo.sujet_id.in_(joueur_ids))
-            if staff_ids:
-                conds.append((Photo.sujet_type == "staff") & Photo.sujet_id.in_(staff_ids))
-            if conds:
-                photos = (await db.execute(select(Photo).where(or_(*conds)))).scalars().all()
-                for ph in photos:
-                    if sup_photo is not None:
-                        try:
-                            await sup_photo(ph.storage_key)
-                            rapport["objets_photos"] += 1
-                        except Exception:
-                            pass
-                    await db.delete(ph)
-                    rapport["photos"] += 1
-            etape = "suppression_joueurs"
-            for j in joueurs:
-                await db.delete(j)
-            rapport["joueurs"] = len(joueurs)
-            etape = "suppression_staffs"
-            for m in staffs:
-                await db.delete(m)
-            rapport["staffs"] = len(staffs)
-            etape = "suppression_clubs"
-            marque = "/object/public/logos-clubs/"
-            for c in clubs_demo:
-                if c.logo_url and marque in c.logo_url:
-                    try:
-                        await stockage_logo.supprimer_objet(c.logo_url.split(marque)[-1])
-                        rapport["objets_logos"] += 1
-                    except Exception:
-                        pass
-                await db.delete(c)
-            rapport["clubs"] = len(clubs_demo)
-        etape = "orga_competitions"
-        user_ids = [u.id for u in users_demo]
-        if user_ids:
-            lignes = (await db.execute(
-                select(OrganisateurCompetition).where(OrganisateurCompetition.user_id.in_(user_ids))
-            )).scalars().all()
-            for lg in lignes:
-                await db.delete(lg)
-        etape = "suppression_users"
-        for u in users_demo:
-            await db.delete(u)
-        rapport["users"] = len(users_demo)
-        etape = "audit"
-        await log_audit(db, "purge", 0, ActionAudit.DELETE, None, None, rapport)
-        etape = "commit"
-        await db.commit()
-    except Exception as ex:
-        await db.rollback()
-        return {"erreur": str(ex), "etape": etape, "rapport_partiel": rapport}
-    return rapport
```

## backend/app/routes/competitions.py
```diff
@@ -19,10 +19,10 @@
 
 
 @router.get("/competitions", response_model=list[CompetitionOut])
-async def lister_competitions(db: AsyncSession = Depends(get_db), inclure_demo: bool = False):
-    query = select(Competition)
-    if not inclure_demo:
-        query = query.where(Competition.est_demo.is_(False))
+async def lister_competitions(db: AsyncSession = Depends(get_db)):
+    # Les compétitions de démonstration ne sont plus jamais listées
+    # (l'ancien paramètre inclure_demo a été supprimé avec l'environnement démo).
+    query = select(Competition).where(Competition.est_demo.is_(False))
     result = await db.execute(query)
     return result.scalars().all()
 
```

## backend/app/routes/matchs.py
```diff
@@ -424,7 +424,7 @@
     match_ = await db.get(Match, match_id)
     if not match_:
         raise HTTPException(status_code=404, detail="Match introuvable.")
-    if match_.locked or getattr(match_.statut, "value", match_.statut) in ("termine", "valide"):
+    if match_.locked or getattr(match_.statut, "value", match_.statut) in ("en_cours", "termine", "valide"):
         raise HTTPException(status_code=400, detail="Match verrouillé : composition non modifiable.")
     equipe = getattr(payload.equipe, "value", payload.equipe)
     club_id = match_.equipe_domicile_id if equipe == "domicile" else match_.equipe_exterieur_id
```

## backend/app/main.py
```diff
@@ -21,6 +21,7 @@
     public,
     stats,
     sync,
+    utilisateurs,
     validation,
 )
 
@@ -59,6 +60,7 @@
 app.include_router(stats.router, prefix=PREFIX)
 app.include_router(sync.router, prefix=PREFIX)
 app.include_router(audit.router, prefix=PREFIX)
+app.include_router(utilisateurs.router, prefix=PREFIX)
 
 
 @app.api_route("/health", methods=["GET", "HEAD"], tags=["Santé"])
```

## backend/alembic/versions/0011_activation.py
```diff
(fichier NOUVEAU — absent de ta base)
+ (voir le fichier joint dans le paquet)
```

## frontend-web/src/api.js
```diff
@@ -56,7 +56,7 @@
 }
 
 export const api = {
-  competitions: () => request("/competitions?inclure_demo=true"),
+  competitions: () => request("/competitions"),
   creerCompetition: (payload) => request("/competitions", { method: "POST", body: payload, auth: true }),
   supprimerCompetition: (id) => request(`/competitions/${id}`, { method: "DELETE", auth: true }),
   saisons: (competitionId) => request(`/saisons?competition_id=${competitionId}`),
@@ -187,6 +187,24 @@
     request(`/matchs/${id}/participations/${pid}`, { method: "DELETE", auth: true }),
   saisirEvenement: (matchId, payload) =>
     request(`/matchs/${matchId}/evenements`, { method: "POST", body: payload, auth: true }),
+  // Comptes réels (admin) + activation + mot de passe personnel.
+  // Aucune de ces fonctions ne transporte un mot de passe existant :
+  // l'admin ne voit jamais que des codes d'activation à usage unique.
+  utilisateurs: () => request("/admin/utilisateurs", { auth: true }),
+  creerUtilisateur: (payload) =>
+    request("/admin/utilisateurs", { method: "POST", body: payload, auth: true }),
+  reinitialiserUtilisateur: (id) =>
+    request(`/admin/utilisateurs/${id}/reinitialiser`, { method: "POST", auth: true }),
+  modifierUtilisateur: (id, payload) =>
+    request(`/admin/utilisateurs/${id}`, { method: "PATCH", body: payload, auth: true }),
+  activerCompte: (email, jeton, mot_de_passe) =>
+    request("/auth/activation", { method: "POST", body: { email, jeton, mot_de_passe } }),
+  changerMotDePasse: (mot_de_passe_actuel, nouveau_mot_de_passe) =>
+    request("/auth/changer-mot-de-passe", {
+      method: "POST",
+      body: { mot_de_passe_actuel, nouveau_mot_de_passe },
+      auth: true,
+    }),
 };
 
 export async function uploadFichier(path, fichier) {
```

## frontend-web/src/portes.js
```diff
@@ -1,35 +1,3 @@
-import { api } from "./api.js";
-
-export const MDP_DEMO = "ChangeMoiEnDemo123!";
-
-export const COMPTES_TEST = [
-  {
-    label: "Collecteur",
-    email: "collecteur.demo@example.com",
-    porte: "/collecteur",
-  },
-  {
-    label: "Club",
-    email: "manager.demo@example.com",
-    porte: "/club",
-  },
-  {
-    label: "Coach",
-    email: "coach.demo@example.com",
-    porte: "/coach",
-  },
-  {
-    label: "Organisateur",
-    email: "orga.demo@example.com",
-    porte: "/orga",
-  },
-  {
-    label: "Admin",
-    email: "admin.demo@example.com",
-    porte: "/admin",
-  },
-];
-
 export function porteDuRole(role) {
   if (role === "collecteur") return "/collecteur";
   if (role === "club_manager") return "/club";
@@ -38,8 +6,3 @@
   if (role === "admin") return "/admin";
   return "/";
 }
-
-export async function connecterCompteTest(email, applySession) {
-  const tokens = await api.login(email, MDP_DEMO);
-  return applySession(tokens);
-}
```

## frontend-web/src/App.jsx
```diff
@@ -39,6 +39,8 @@
 import AdminVue from "./pages/admin/Vue.jsx";
 import AdminAudit from "./pages/admin/Audit.jsx";
 import AdminPropositions from "./pages/admin/Propositions.jsx";
+import AdminComptes from "./pages/admin/Comptes.jsx";
+import Activation from "./pages/Activation.jsx";
 import { AuthProvider, useAuth } from "./auth.jsx";
 import { isAuthenticated } from "./api.js";
 
@@ -84,6 +86,7 @@
             <Route path="/recherche" element={<Recherche />} />
           </Route>
           <Route path="/login" element={<Login />} />
+          <Route path="/activation" element={<Activation />} />
           <Route
             path="/orga"
             element={
@@ -138,6 +141,7 @@
             <Route path="staff" element={<ClubCoach />} />
             <Route path="matchs" element={<CoachMatchs />} />
             <Route path="matchs/:id" element={<CoachMatch />} />
+            <Route path="matchs/:matchId/composition" element={<ClubComposition />} />
           </Route>
           <Route
             path="/admin"
@@ -150,6 +154,7 @@
             <Route index element={<AdminVue />} />
             <Route path="audit" element={<AdminAudit />} />
             <Route path="propositions" element={<AdminPropositions />} />
+            <Route path="comptes" element={<AdminComptes />} />
           </Route>
           <Route path="*" element={<Navigate to="/" replace />} />
         </Routes>
```

## frontend-web/src/styles.css
```diff
@@ -2551,3 +2551,14 @@
 
 /* --- Competition unique en texte, ajout pack-championnat-unique --- */
 .comp-nom{margin:.5rem 1rem 0;color:color-mix(in srgb,var(--cream) 80%,transparent);font-size:.86rem;letter-spacing:.03em}
+
+/* --- Comptes réels : activation, comptes admin, mot de passe (12 septembre) — lignes ajoutées --- */
+.jeton-boite{margin:1rem 0;padding:1rem .2rem;border-top:1.5px solid var(--stamp);border-bottom:1.5px solid var(--stamp)}
+.jeton-code{margin:.6rem 0;padding:.7rem .8rem;border:1px dashed var(--rule-strong);font-family:ui-monospace,Menlo,Consolas,monospace;font-size:1rem;letter-spacing:.04em;word-break:break-all;color:var(--ink);user-select:all}
+.jeton-actions{display:flex;flex-wrap:wrap;gap:.9rem;align-items:center;margin:.4rem 0 0}
+.jeton-actions .btn{width:auto;padding:.55rem .9rem}
+.jeton-saisie{font-family:ui-monospace,Menlo,Consolas,monospace;letter-spacing:.03em}
+.comptes-form{margin:1rem 0;padding:1rem 0}
+.compte-ligne-actions{display:flex;gap:.9rem;align-items:center;flex-shrink:0}
+.avenir-row .btn{width:auto;flex-shrink:0;padding:.55rem .9rem}
+.compte-mdp{margin-top:1.1rem}
```

## frontend-web/src/components/AdminLayout.jsx
```diff
@@ -26,6 +26,7 @@
         <NavLink to="/admin" end>Vue</NavLink>
         <NavLink to="/admin/audit">Audit</NavLink>
         <NavLink to="/admin/propositions">Propositions</NavLink>
+        <NavLink to="/admin/comptes">Comptes</NavLink>
       </nav>
       <div className="shell">
         <Outlet />
```

## frontend-web/src/pages/Login.jsx
```diff
@@ -3,7 +3,6 @@
 import { api } from "../api.js";
 import { useAuth } from "../auth.jsx";
 import { porteDuRole } from "../portes.js";
-import ComptesTest from "../components/ComptesTest.jsx";
 
 export default function Login() {
   const nav = useNavigate();
@@ -64,12 +63,12 @@
           {busy ? "Connexion…" : "Se connecter"}
         </button>
         <p className="meta" style={{ textAlign: "center", marginTop: "1rem" }}>
+          <Link to="/activation">Première connexion ? Activer mon compte</Link>
+        </p>
+        <p className="meta" style={{ textAlign: "center" }}>
           <Link to="/">← Retour au site public</Link>
         </p>
       </form>
-      <div className="login-card">
-        <ComptesTest />
-      </div>
     </div>
   );
 }
```

## frontend-web/src/pages/Activation.jsx
```diff
(fichier NOUVEAU — absent de ta base)
+ (voir le fichier joint dans le paquet)
```

## frontend-web/src/pages/Compte.jsx
```diff
@@ -82,6 +82,38 @@
   const [err, setErr] = useState("");
   const [fieldErr, setFieldErr] = useState({});
   const [busy, setBusy] = useState(false);
+  const [mdpActuel, setMdpActuel] = useState("");
+  const [mdpNeuf, setMdpNeuf] = useState("");
+  const [mdpNeuf2, setMdpNeuf2] = useState("");
+  const [mdpErr, setMdpErr] = useState("");
+  const [mdpMsg, setMdpMsg] = useState("");
+  const [mdpBusy, setMdpBusy] = useState(false);
+
+  async function changerMdp(e) {
+    e.preventDefault();
+    setMdpErr("");
+    setMdpMsg("");
+    if (mdpNeuf.length < 8) {
+      setMdpErr("Au moins 8 caractères.");
+      return;
+    }
+    if (mdpNeuf !== mdpNeuf2) {
+      setMdpErr("Les deux mots de passe ne correspondent pas.");
+      return;
+    }
+    setMdpBusy(true);
+    try {
+      await api.changerMotDePasse(mdpActuel, mdpNeuf);
+      setMdpActuel("");
+      setMdpNeuf("");
+      setMdpNeuf2("");
+      setMdpMsg("Mot de passe changé. Les autres appareils devront se reconnecter.");
+    } catch (ex) {
+      setMdpErr(ex.message || "Changement impossible.");
+    } finally {
+      setMdpBusy(false);
+    }
+  }
 
   async function onLogout() {
     await logout();
@@ -216,6 +248,50 @@
             )}
           </div>
         )}
+        <div className="sheet compte-mdp" style={{ marginTop: "1.1rem" }}>
+          <div className="section-head">
+            <h2>Mot de passe</h2>
+          </div>
+          <form className="compte-form" onSubmit={changerMdp}>
+            <label className="field">
+              Mot de passe actuel
+              <input
+                type="password"
+                autoComplete="current-password"
+                value={mdpActuel}
+                onChange={(e) => setMdpActuel(e.target.value)}
+                required
+              />
+            </label>
+            <label className="field">
+              Nouveau mot de passe (8 caractères minimum)
+              <input
+                type="password"
+                autoComplete="new-password"
+                value={mdpNeuf}
+                onChange={(e) => setMdpNeuf(e.target.value)}
+                required
+                minLength={8}
+              />
+            </label>
+            <label className="field">
+              Confirmer le nouveau mot de passe
+              <input
+                type="password"
+                autoComplete="new-password"
+                value={mdpNeuf2}
+                onChange={(e) => setMdpNeuf2(e.target.value)}
+                required
+                minLength={8}
+              />
+            </label>
+            {mdpErr && <p className="erreur">{mdpErr}</p>}
+            {mdpMsg && <p className="empty">{mdpMsg}</p>}
+            <button className="btn btn-primary" type="submit" disabled={mdpBusy}>
+              {mdpBusy ? "Changement…" : "Changer mon mot de passe"}
+            </button>
+          </form>
+        </div>
         <p className="id-out">
           <Link to="/matchs">Matchs</Link>
           {" · "}
```

## frontend-web/src/pages/admin/Comptes.jsx
```diff
(fichier NOUVEAU — absent de ta base)
+ (voir le fichier joint dans le paquet)
```

## frontend-web/src/pages/coach/Match.jsx
```diff
@@ -4,6 +4,7 @@
 import { useAuth } from "../../auth.jsx";
 import { clubName, useKivu } from "../../context.jsx";
 import { stripDemo } from "../../display.js";
+import { fmtQuand, STATUT_MATCH } from "../orga/saison.js";
 
 export default function CoachMatch() {
   const { id } = useParams();
@@ -11,37 +12,13 @@
   const { clubsById } = useKivu();
   const clubId = user?.club_id;
   const [match, setMatch] = useState(null);
-  const [joueurs, setJoueurs] = useState([]);
-  const [autresJoueurs, setAutresJoueurs] = useState([]);
-  const [parts, setParts] = useState([]);
-  const [draft, setDraft] = useState({});
+  const [compo, setCompo] = useState(null);
   const [err, setErr] = useState("");
-  const [msg, setMsg] = useState("");
-  const [busy, setBusy] = useState(false);
-
-  async function load() {
-    const m = await api.match(id);
-    setMatch(m);
-    const otherId = clubId === m.equipe_domicile_id ? m.equipe_exterieur_id : m.equipe_domicile_id;
-    const [js, autres, p] = await Promise.all([
-      clubId ? api.joueurs(clubId).catch(() => []) : [],
-      otherId ? api.joueurs(otherId).catch(() => []) : [],
-      api.participations(id).catch(() => []),
-    ]);
-    setJoueurs(js || []);
-    setAutresJoueurs(autres || []);
-    setParts(p || []);
-    const d = {};
-    (p || []).forEach((x) => {
-      if (x.club_id === clubId) d[x.joueur_id] = x.statut;
-    });
-    setDraft(d);
-  }
 
   useEffect(() => {
     if (!clubId) return;
-    load().catch((e) => setErr(e.message));
-    // eslint-disable-next-line react-hooks/exhaustive-deps
+    api.match(id).then(setMatch).catch((e) => setErr(e.message));
+    api.composition(id).then(setCompo).catch(() => setCompo(null));
   }, [id, clubId]);
 
   if (!clubId) return <p className="empty">Aucun club rattaché.</p>;
@@ -50,110 +27,51 @@
   const home = stripDemo(clubName(clubsById, match.equipe_domicile_id));
   const away = stripDemo(clubName(clubsById, match.equipe_exterieur_id));
   const cote = clubId === match.equipe_domicile_id ? "domicile" : "exterieur";
-  const moi = cote === "domicile" ? home : away;
-  const locked = match.locked || match.statut === "valide";
-
-  function cycle(jid) {
-    if (locked) return;
-    setDraft((d) => {
-      const cur = d[jid];
-      const next = cur === "titulaire" ? "remplacant" : cur === "remplacant" ? "" : "titulaire";
-      const copy = { ...d };
-      if (!next) delete copy[jid];
-      else copy[jid] = next;
-      return copy;
-    });
-  }
-
-  function badge(jid) {
-    const st = draft[jid];
-    if (st === "titulaire") return "Titu";
-    if (st === "remplacant") return "Banc";
-    return "—";
-  }
-
-  async function enregistrer() {
-    setBusy(true);
-    setErr("");
-    setMsg("");
-    try {
-      const mine = parts.filter((p) => p.club_id === clubId);
-      const byJoueur = Object.fromEntries(mine.map((p) => [p.joueur_id, p]));
-      for (const j of joueurs) {
-        const want = draft[j.id];
-        const have = byJoueur[j.id];
-        if (!want && have) {
-          await api.retirerParticipation(id, have.id);
-        } else if (want && !have) {
-          await api.ajouterParticipation(id, {
-            joueur_id: j.id,
-            club_id: clubId,
-            equipe_concernee: cote,
-            statut: want,
-            minute_entree: 0,
-          });
-        } else if (want && have && have.statut !== want) {
-          await api.modifierParticipation(id, have.id, { statut: want });
-        }
-      }
-      setMsg("Composition enregistrée.");
-      await load();
-    } catch (ex) {
-      setErr(ex.message);
-    } finally {
-      setBusy(false);
-    }
-  }
-
   const autreCote = cote === "domicile" ? "exterieur" : "domicile";
-  const autreParts = parts.filter((p) => p.equipe_concernee === autreCote);
-  const autreNom = cote === "domicile" ? away : home;
+  const verrouille = match.locked || ["en_cours", "termine", "valide"].includes(match.statut);
+  const bloc = compo?.[cote];
+  const autreBloc = compo?.[autreCote];
 
   return (
     <section className="hero">
       <p className="kicker"><Link to="/coach/matchs">← Matchs</Link></p>
       <h1>{home} · {away}</h1>
-      <p className="lead">Votre équipe seulement : {moi}. Toucher un nom : titulaire, banc, ou rien.</p>
+      <p className="lead">
+        {[STATUT_MATCH[match.statut] || match.statut, fmtQuand(match.date_heure)].filter(Boolean).join(" · ")}
+      </p>
       {err && <p className="erreur">{err}</p>}
-      {msg && <p className="empty">{msg}</p>}
-      {locked && <p className="empty">Match verrouillé — plus aucune modification.</p>}
+      {verrouille && (
+        <p className="empty">Match verrouillé — la feuille ne peut plus être modifiée.</p>
+      )}
 
-      <div className="section-head">
-        <h2>{moi}</h2>
+      <div className="sheet" style={{ marginTop: "1rem" }}>
+        <div className="avenir-row">
+          <span className="avenir-noms">
+            <span>Feuille de composition</span>
+            <span className="meta-line">
+              {bloc
+                ? `Titulaires ${(bloc.titulaires || []).length}/11 · Banc ${(bloc.banc || []).length}/${compo?.max_remplacants ?? "—"}${bloc.formation ? ` · ${bloc.formation}` : ""}${bloc.staff ? ` · ${bloc.staff.nom_complet || ""}` : ""}`
+                : "Pas encore de feuille"}
+            </span>
+          </span>
+          <Link className="btn btn-primary" to={`/coach/matchs/${id}/composition`}>
+            {verrouille ? "Voir la feuille" : "Composition"}
+          </Link>
+        </div>
       </div>
-      {joueurs.length === 0 && <p className="empty">Aucun joueur dans l’effectif. L’effectif se tient au club.</p>}
-      {joueurs.map((j) => (
-        <button
-          key={j.id}
-          type="button"
-          className="comp-row"
-          disabled={locked || busy}
-          onClick={() => cycle(j.id)}
-        >
-          <span>{j.nom_complet}</span>
-          <strong>{badge(j.id)}</strong>
-        </button>
-      ))}
-      {!locked && (
-        <button className="btn btn-primary" type="button" disabled={busy} onClick={enregistrer} style={{ marginTop: "0.8rem" }}>
-          {busy ? "…" : "Enregistrer la composition"}
-        </button>
-      )}
 
-      <div className="section-head">
-        <h2>{autreNom}</h2>
+      <div className="section-head" style={{ marginTop: "1.2rem" }}>
+        <h2>{autreCote === "domicile" ? home : away}</h2>
       </div>
       <p className="lead">L’autre composition. Vous ne la posez pas.</p>
-      {autreParts.length === 0 && <p className="empty">Composition à compléter</p>}
-      {autreParts.map((p) => {
-        const j = autresJoueurs.find((x) => x.id === p.joueur_id);
-        return (
-          <div key={p.id} className="comp-row">
-            <span>{j?.nom_complet || "à compléter"}</span>
-            <strong>{p.statut === "titulaire" ? "Titu" : "Banc"}</strong>
-          </div>
-        );
-      })}
+      {!autreBloc || ((autreBloc.titulaires || []).length === 0 && (autreBloc.banc || []).length === 0) ? (
+        <p className="empty">Composition à compléter</p>
+      ) : (
+        <p className="empty">
+          Titulaires {(autreBloc.titulaires || []).length} · Banc {(autreBloc.banc || []).length}
+          {autreBloc.formation ? ` · ${autreBloc.formation}` : ""}
+        </p>
+      )}
 
       <p className="id-out">
         <Link to={`/matchs/${id}`}>Voir le match public</Link>
```

## frontend-web/src/components/ComptesTest.jsx
```diff
- (fichier SUPPRIMÉ : carte des comptes de test, plus importée nulle part)
```
