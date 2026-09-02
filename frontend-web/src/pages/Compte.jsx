import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

export default function Compte() {
  const nav = useNavigate();
  const { user, applySession, logout } = useAuth();
  const [mode, setMode] = useState("connexion");
  const [nom, setNom] = useState("");
  const [email, setEmail] = useState("");
  const [mdp, setMdp] = useState("");
  const [mdp2, setMdp2] = useState("");
  const [err, setErr] = useState("");
  const [fieldErr, setFieldErr] = useState({});
  const [busy, setBusy] = useState(false);

  async function onLogout() {
    await logout();
    nav("/", { replace: true });
  }

  async function onSubmit(e) {
    e.preventDefault();
    setErr("");
    const fe = {};
    if (mode === "creer") {
      if (!nom.trim() || nom.trim().length < 2) fe.nom = "Indiquez votre nom complet.";
      if (mdp.length < 8) fe.mdp = "Au moins 8 caractères.";
      if (mdp !== mdp2) fe.mdp2 = "Les mots de passe ne correspondent pas.";
    }
    if (!email.trim()) fe.email = "Indiquez votre e-mail.";
    if (!mdp) fe.mdp = fe.mdp || "Indiquez un mot de passe.";
    setFieldErr(fe);
    if (Object.keys(fe).length) return;

    setBusy(true);
    try {
      const tokens =
        mode === "creer"
          ? await api.register(nom.trim(), email.trim(), mdp)
          : await api.login(email.trim(), mdp);
      await applySession(tokens);
      nav("/", { replace: true });
    } catch (ex) {
      setErr(ex.message || "Impossible de continuer.");
    } finally {
      setBusy(false);
    }
  }

  if (user) {
    return (
      <section className="hero">
        <p className="kicker"><Link to="/">← Accueil</Link></p>
        <h1>Compte</h1>
        <p className="lead">{user.nom_complet || user.email}</p>
        <p className="journee-date">{user.email}</p>
        <button className="linkish" type="button" onClick={onLogout}>
          Se déconnecter
        </button>
      </section>
    );
  }

  return (
    <section className="hero">
      <p className="kicker"><Link to="/">← Accueil</Link></p>
      <h1>Compte</h1>
      <p className="lead">Les matchs et classements restent lisibles sans compte.</p>

      <div className="compte-tabs">
        <button
          type="button"
          className={mode === "connexion" ? "on" : ""}
          onClick={() => { setMode("connexion"); setErr(""); }}
        >
          Connexion
        </button>
        <button
          type="button"
          className={mode === "creer" ? "on" : ""}
          onClick={() => { setMode("creer"); setErr(""); }}
        >
          Créer un compte
        </button>
      </div>

      <form className="compte-form" onSubmit={onSubmit}>
        {mode === "creer" && (
          <label className="field">
            Nom complet
            <input
              value={nom}
              onChange={(e) => setNom(e.target.value)}
              autoComplete="name"
              placeholder="Ex. Yves Bukasa"
            />
            {fieldErr.nom && <span className="erreur">{fieldErr.nom}</span>}
          </label>
        )}
        <label className="field">
          E-mail
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            placeholder="vous@exemple.com"
            required
          />
          {fieldErr.email && <span className="erreur">{fieldErr.email}</span>}
        </label>
        <label className="field">
          Mot de passe
          <input
            type="password"
            value={mdp}
            onChange={(e) => setMdp(e.target.value)}
            autoComplete={mode === "creer" ? "new-password" : "current-password"}
            required
          />
          {fieldErr.mdp && <span className="erreur">{fieldErr.mdp}</span>}
        </label>
        {mode === "creer" && (
          <label className="field">
            Confirmer le mot de passe
            <input
              type="password"
              value={mdp2}
              onChange={(e) => setMdp2(e.target.value)}
              autoComplete="new-password"
            />
            {fieldErr.mdp2 && <span className="erreur">{fieldErr.mdp2}</span>}
          </label>
        )}
        {err && <p className="erreur">{err}</p>}
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy
            ? "…"
            : mode === "creer"
              ? "Créer le compte"
              : "Se connecter"}
        </button>
      </form>
      {mode === "connexion" && (
        <p className="meta" style={{ marginTop: "1rem" }}>
          <button className="linkish" type="button" onClick={() => setMode("creer")}>
            Pas encore de compte ? Créer un compte
          </button>
        </p>
      )}
    </section>
  );
}
