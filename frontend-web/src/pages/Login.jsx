import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

export default function Login() {
  const nav = useNavigate();
  const { applySession } = useAuth();
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      const tokens = await api.login(email.trim(), motDePasse);
      await applySession(tokens);
      nav("/", { replace: true });
    } catch (ex) {
      setErr(ex.message || "Connexion impossible");
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
        <h1>Bon retour</h1>
        <p className="sub">Connexion. L’Accueil ensuite.</p>
        <label className="field">
          Adresse e-mail
          <input
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            placeholder="vous@championnat.cd"
          />
        </label>
        <label className="field">
          Mot de passe
          <input
            type="password"
            autoComplete="current-password"
            value={motDePasse}
            onChange={(e) => setMotDePasse(e.target.value)}
            required
            placeholder="••••••••"
          />
        </label>
        {err && <p className="erreur">{err}</p>}
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Connexion…" : "Se connecter"}
        </button>
        <p className="meta" style={{ textAlign: "center", marginTop: "1rem" }}>
          <Link to="/">← Retour au site public</Link>
        </p>
      </form>
    </div>
  );
}
