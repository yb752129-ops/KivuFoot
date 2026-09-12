import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { porteDuRole } from "../portes.js";

export default function Activation() {
  const nav = useNavigate();
  const { applySession } = useAuth();
  const [email, setEmail] = useState("");
  const [jeton, setJeton] = useState("");
  const [mdp, setMdp] = useState("");
  const [mdp2, setMdp2] = useState("");
  const [voir, setVoir] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setErr("");
    if (mdp.length < 8) {
      setErr("Le mot de passe doit contenir au moins 8 caractères.");
      return;
    }
    if (mdp !== mdp2) {
      setErr("Les deux mots de passe ne correspondent pas.");
      return;
    }
    setBusy(true);
    try {
      const tokens = await api.activerCompte(email.trim(), jeton.trim(), mdp);
      const me = await applySession(tokens);
      nav(porteDuRole(me?.role), { replace: true });
    } catch (ex) {
      setErr(ex.message || "Activation impossible.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={onSubmit}>
        <div className="brand" style={{ marginBottom: "1.1rem" }}>
          <span className="brand-mark">KF</span>
          KivuFoot
        </div>
        <h1>Activer mon compte</h1>
        <p className="sub">
          Utilisez le code transmis par l’administrateur, puis choisissez votre
          mot de passe personnel. Personne d’autre ne le connaîtra.
        </p>
        <label className="field">
          Adresse e-mail du compte
          <input
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            placeholder="vous@club.cd"
          />
        </label>
        <label className="field">
          Code d’activation
          <input
            type="text"
            value={jeton}
            onChange={(e) => setJeton(e.target.value)}
            required
            autoComplete="one-time-code"
            placeholder="Code à usage unique"
            className="jeton-saisie"
          />
        </label>
        <label className="field">
          <span className="field-top">
            Votre mot de passe
            <button type="button" className="linkish" onClick={() => setVoir((v) => !v)}>
              {voir ? "Masquer" : "Afficher"}
            </button>
          </span>
          <input
            type={voir ? "text" : "password"}
            autoComplete="new-password"
            value={mdp}
            onChange={(e) => setMdp(e.target.value)}
            required
            minLength={8}
            placeholder="••••••••"
          />
        </label>
        <label className="field">
          Confirmez le mot de passe
          <input
            type={voir ? "text" : "password"}
            autoComplete="new-password"
            value={mdp2}
            onChange={(e) => setMdp2(e.target.value)}
            required
            minLength={8}
            placeholder="••••••••"
          />
        </label>
        {err && <p className="erreur">{err}</p>}
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Activation…" : "Activer et choisir mon mot de passe"}
        </button>
        <p className="meta" style={{ textAlign: "center", marginTop: "1rem" }}>
          <Link to="/login">← J’ai déjà un mot de passe</Link>
        </p>
      </form>
    </div>
  );
}
