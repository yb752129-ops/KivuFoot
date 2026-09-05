import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { clubName, useKivu } from "../context.jsx";
import { stripDemo } from "../display.js";
import { useTheme } from "../theme.jsx";
import { COMPTES_TEST, MDP_DEMO, porteDuRole } from "../portes.js";

const ROLE_LIBELLE = {
  supporter: "Lecteur",
  organisateur: "Organisateur",
  admin: "Administration",
  collecteur: "Collecteur",
  club_manager: "Club",
};

const THEMES = [
  { id: "light", label: "Clair" },
  { id: "dark", label: "Sombre" },
  { id: "system", label: "Système" },
];

function Apparence() {
  const theme = useTheme();
  if (!theme) return null;
  return (
    <section className="apparence">
      <div className="section-head">
        <h2>Apparence</h2>
      </div>
      <div className="theme-picks" role="radiogroup" aria-label="Thème">
        {THEMES.map((t) => (
          <button
            key={t.id}
            type="button"
            role="radio"
            aria-checked={theme.choice === t.id}
            className={theme.choice === t.id ? "on" : ""}
            onClick={() => theme.setChoice(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
    </section>
  );
}

function MotDePasse({ value, onChange, autoComplete, error }) {
  const [voir, setVoir] = useState(false);
  return (
    <label className="field">
      <span className="field-top">
        Mot de passe
        <button type="button" className="linkish" onClick={() => setVoir((v) => !v)}>
          {voir ? "Masquer" : "Afficher"}
        </button>
      </span>
      <input
        type={voir ? "text" : "password"}
        value={value}
        onChange={onChange}
        autoComplete={autoComplete}
        required
      />
      {error && <span className="erreur">{error}</span>}
    </label>
  );
}

export default function Compte() {
  const nav = useNavigate();
  const { user, applySession, logout } = useAuth();
  const { clubsById } = useKivu();
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
      const me = await applySession(tokens);
      nav(porteDuRole(me?.role), { replace: true });
    } catch (ex) {
      setErr(ex.message || "Impossible de continuer.");
    } finally {
      setBusy(false);
    }
  }

  if (user) {
    const initiale = (user.nom_complet || user.email || "?")
      .trim()
      .charAt(0)
      .toUpperCase();
    const role = user.role || "supporter";
    const statut = ROLE_LIBELLE[role] || "Lecteur";
    const club = user.club_id ? stripDemo(clubName(clubsById, user.club_id)) : "";
    const staff = role === "organisateur" || role === "admin" || role === "collecteur";
    const orga = role === "organisateur" || role === "admin";
    const collecte = role === "collecteur" || role === "admin";
    const clubPorte = role === "club_manager";
    return (
      <section className="hero">
        <p className="kicker"><Link to="/">← Accueil</Link></p>
        <div className="id-head">
          <span className="id-mark" aria-hidden="true">{initiale}</span>
          <div>
            <h1>{user.nom_complet || "Compte"}</h1>
            <p className="journee-date">{statut} — Sud-Kivu</p>
          </div>
        </div>
        <p className="lead">
          {clubPorte
            ? "Ce compte tient l’effectif du club. Le public lit sans se connecter."
            : staff
              ? "Ce compte ouvre la saisie des matchs. Le public lit sans se connecter."
              : "Les matchs, le classement et les clubs restent lisibles sans compte. Celui-ci sert à vous reconnaître."}
        </p>
        <div className="sheet id-sheet">
          <div className="id-row">
            <span>Nom</span>
            <strong>{user.nom_complet || "—"}</strong>
          </div>
          <div className="id-row">
            <span>E-mail</span>
            <strong>{user.email}</strong>
          </div>
          <div className="id-row">
            <span>Statut</span>
            <strong>{statut}</strong>
          </div>
          {club && (
            <div className="id-row">
              <span>Club</span>
              <strong>{club}</strong>
            </div>
          )}
        </div>
        {(orga || collecte || clubPorte) && (
          <div className="sheet" style={{ marginTop: "1.1rem" }}>
            {orga && (
              <Link to="/orga" className="avenir-row">
                <span className="avenir-noms">
                  <span>Organisation</span>
                  <span className="meta-line">/orga</span>
                </span>
              </Link>
            )}
            {collecte && (
              <Link to="/collecteur" className="avenir-row">
                <span className="avenir-noms">
                  <span>Collecte</span>
                  <span className="meta-line">/collecteur</span>
                </span>
              </Link>
            )}
            {clubPorte && (
              <Link to="/club" className="avenir-row">
                <span className="avenir-noms">
                  <span>Club</span>
                  <span className="meta-line">/club</span>
                </span>
              </Link>
            )}
          </div>
        )}
        <p className="id-out">
          <Link to="/matchs">Matchs</Link>
          {" · "}
          <Link to="/classement">Classement</Link>
        </p>
        <p className="id-out" style={{ borderTop: 0, marginTop: 0, paddingTop: "0.2rem" }}>
          <button className="linkish" type="button" onClick={onLogout}>
            Se déconnecter
          </button>
        </p>
        <Apparence />
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
            required
          />
          {fieldErr.email && <span className="erreur">{fieldErr.email}</span>}
        </label>
        <MotDePasse
          value={mdp}
          onChange={(e) => setMdp(e.target.value)}
          autoComplete={mode === "creer" ? "new-password" : "current-password"}
          error={fieldErr.mdp}
        />
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
        <button
          className={`btn btn-primary${busy ? " is-busy" : ""}`}
          type="submit"
          disabled={busy}
        >
          {busy
            ? mode === "creer"
              ? "Création…"
              : "Connexion…"
            : mode === "creer"
              ? "Créer le compte"
              : "Se connecter"}
        </button>
      </form>
      {mode === "connexion" && (
        <p style={{ marginTop: "1.1rem" }}>
          <button className="linkish" type="button" onClick={() => setMode("creer")}>
            Pas encore de compte ? Créer un compte
          </button>
        </p>
      )}
      <Apparence />
    </section>
  );
}
