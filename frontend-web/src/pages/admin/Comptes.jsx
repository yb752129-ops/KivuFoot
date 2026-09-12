import { useEffect, useState } from "react";
import { api } from "../../api.js";
import { stripDemo } from "../../display.js";

const ROLES = [
  { value: "coach", label: "Coach" },
  { value: "club_manager", label: "Club" },
  { value: "collecteur", label: "Collecteur" },
  { value: "organisateur", label: "Organisateur" },
];
const ROLE_LIBELLE = {
  supporter: "Lecteur",
  collecteur: "Collecteur",
  club_manager: "Club",
  coach: "Coach",
  organisateur: "Organisateur",
  admin: "Admin",
};
const ROLES_A_CLUB = ["coach", "club_manager"];

function Jeton({ jeton, contexte, onFermer }) {
  const [copie, setCopie] = useState(false);
  async function copier() {
    try {
      await navigator.clipboard.writeText(jeton);
      setCopie(true);
    } catch {
      setCopie(false);
    }
  }
  return (
    <div className="card jeton-boite">
      <p className="kicker">{contexte}</p>
      <p className="lead">
        Code d’activation à usage unique. Montrez-le une seule fois, transmettez-le
        hors écran. La personne choisira elle-même son mot de passe : vous ne le
        verrez jamais.
      </p>
      <p className="jeton-code" onDoubleClick={copier}>{jeton}</p>
      <p className="jeton-actions">
        <button className="btn btn-primary" type="button" onClick={copier}>
          {copie ? "Copié ✓" : "Copier le code"}
        </button>
        <button className="linkish" type="button" onClick={onFermer}>
          Fermer (le code ne sera plus jamais affiché)
        </button>
      </p>
    </div>
  );
}

export default function AdminComptes() {
  const [users, setUsers] = useState([]);
  const [clubs, setClubs] = useState([]);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [jeton, setJeton] = useState(null);
  const [busy, setBusy] = useState(0);
  const [form, setForm] = useState({ nom_complet: "", email: "", role: "coach", club_id: "" });

  useEffect(() => {
    api.utilisateurs().then(setUsers).catch((e) => setErr(e.message));
    api.clubs().then(setClubs).catch(() => setClubs([]));
  }, []);

  function nomClub(id) {
    return stripDemo(clubs.find((c) => c.id === id)?.nom) || "—";
  }

  async function creer(e) {
    e.preventDefault();
    setErr(""); setMsg("");
    const payload = {
      nom_complet: form.nom_complet.trim(),
      email: form.email.trim(),
      role: form.role,
    };
    if (ROLES_A_CLUB.includes(form.role)) {
      if (!form.club_id) {
        setErr("Choisissez le club de ce compte.");
        return;
      }
      payload.club_id = Number(form.club_id);
    }
    setBusy(-1);
    try {
      const res = await api.creerUtilisateur(payload);
      setJeton({ jeton: res.jeton_activation, contexte: `Compte créé — ${payload.email}` });
      setMsg("Compte créé. Transmettez le code à la personne.");
      setForm({ nom_complet: "", email: "", role: "coach", club_id: "" });
      setUsers(await api.utilisateurs());
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(0);
    }
  }

  async function reinitialiser(u) {
    if (!window.confirm(`Réinitialiser l'accès de ${u.email} ? Toutes ses sessions seront fermées et un nouveau code sera généré.`)) return;
    setErr(""); setMsg(""); setBusy(u.id);
    try {
      const res = await api.reinitialiserUtilisateur(u.id);
      setJeton({ jeton: res.jeton_activation, contexte: `Réinitialisation — ${u.email}` });
      setMsg("Nouveau code généré. L'ancien accès est coupé.");
      setUsers(await api.utilisateurs());
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(0);
    }
  }

  async function basculer(u) {
    setErr(""); setMsg(""); setBusy(u.id);
    try {
      await api.modifierUtilisateur(u.id, { est_actif: !u.est_actif });
      setMsg(u.est_actif ? "Compte désactivé." : "Compte réactivé.");
      setUsers(await api.utilisateurs());
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(0);
    }
  }

  return (
    <section className="hero">
      <p className="kicker">Administration</p>
      <h1>Comptes</h1>
      <p className="lead">
        Les comptes réels du championnat. Vous ne choisissez et ne voyez jamais
        un mot de passe : chaque personne choisit le sien avec son code.
      </p>
      {err && <p className="erreur">{err}</p>}
      {msg && <p className="empty">{msg}</p>}

      {jeton && (
        <Jeton
          jeton={jeton.jeton}
          contexte={jeton.contexte}
          onFermer={() => setJeton(null)}
        />
      )}

      <form className="card comptes-form" onSubmit={creer}>
        <div className="section-head"><h2>Créer un compte</h2></div>
        <label className="field">
          Nom complet
          <input
            value={form.nom_complet}
            onChange={(e) => setForm((f) => ({ ...f, nom_complet: e.target.value }))}
            required
            minLength={2}
            placeholder="Prénom Nom"
          />
        </label>
        <label className="field">
          Adresse e-mail
          <input
            type="email"
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            required
            placeholder="coach@club.cd"
          />
        </label>
        <label className="field">
          Rôle
          <select
            value={form.role}
            onChange={(e) => setForm((f) => ({ ...f, role: e.target.value, club_id: "" }))}
          >
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>{r.label}</option>
            ))}
          </select>
        </label>
        {ROLES_A_CLUB.includes(form.role) && (
          <label className="field">
            Club
            <select
              value={form.club_id}
              onChange={(e) => setForm((f) => ({ ...f, club_id: e.target.value }))}
              required
            >
              <option value="">— Choisir —</option>
              {clubs.map((c) => (
                <option key={c.id} value={c.id}>{stripDemo(c.nom)}</option>
              ))}
            </select>
          </label>
        )}
        <button className="btn btn-primary" type="submit" disabled={busy === -1}>
          {busy === -1 ? "Création…" : "Créer le compte"}
        </button>
      </form>

      <div className="section-head" style={{ marginTop: "1.4rem" }}>
        <h2>Comptes existants</h2>
      </div>
      {users.length === 0 && <p className="empty">Aucun compte.</p>}
      {users.map((u) => (
        <div key={u.id} className="avenir-row">
          <span className="avenir-noms">
            <span>{u.nom_complet || u.email}{!u.est_actif ? " · désactivé" : ""}</span>
            <span className="meta-line">
              {u.email} · {ROLE_LIBELLE[u.role] || u.role}
              {u.club_id ? ` · ${nomClub(u.club_id)}` : ""}
              {u.activation_en_attente ? " · code en attente" : ""}
            </span>
          </span>
          <span className="compte-ligne-actions">
            <button className="linkish" type="button" disabled={busy === u.id} onClick={() => reinitialiser(u)}>
              Réinitialiser
            </button>
            <button className="linkish" type="button" disabled={busy === u.id} onClick={() => basculer(u)}>
              {u.est_actif ? "Désactiver" : "Réactiver"}
            </button>
          </span>
        </div>
      ))}
    </section>
  );
}
