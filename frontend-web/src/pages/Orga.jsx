import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, clearTokens } from "../api.js";
import { clubName, useKivu } from "../context.jsx";

const STATUT = {
  programme: "Programmé",
  en_cours: "En cours",
  termine: "Terminé",
  valide: "Publié",
  conteste: "Contesté",
};

export default function Orga() {
  const nav = useNavigate();
  const { saison, clubsById } = useKivu();
  const [me, setMe] = useState(null);
  const [file, setFile] = useState([]);
  const [matchs, setMatchs] = useState([]);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  async function load() {
    setErr("");
    try {
      const user = await api.me();
      setMe(user);
      const [ev, ms] = await Promise.all([
        api.fileValidation(),
        saison ? api.matchsGestion(saison.id) : Promise.resolve([]),
      ]);
      setFile(ev);
      setMatchs(ms);
    } catch (e) {
      setErr(e.message);
      if (e.status === 401) {
        clearTokens();
        nav("/login", { replace: true });
      }
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [saison]);

  async function valider(id) {
    setMsg("");
    try {
      await api.validerEvenement(id);
      setMsg("Événement validé.");
      await load();
    } catch (e) {
      setErr(e.message);
    }
  }

  async function rejeter(id) {
    const commentaire = window.prompt("Motif du rejet (obligatoire) :");
    if (!commentaire) return;
    try {
      await api.rejeterEvenement(id, commentaire);
      setMsg("Événement rejeté.");
      await load();
    } catch (e) {
      setErr(e.message);
    }
  }

  function logout() {
    clearTokens();
    nav("/", { replace: true });
  }

  return (
    <div className="shell">
      <header className="topbar" style={{ margin: "0 -1rem 1rem" }}>
        <div className="topbar-inner">
          <Link to="/" className="brand">
            <span className="brand-mark">KF</span>
            Organisateur
          </Link>
          <nav className="nav">
            <span className="meta">{me?.nom_complet || me?.email}</span>
            <button className="linkish" type="button" onClick={logout}>Déconnexion</button>
          </nav>
        </div>
      </header>

      <section className="hero">
        <div className="kicker">Validation</div>
        <h1>Tableau de bord</h1>
        <p className="lead">Rien n’est public tant que vous n’avez pas validé. Un rejet exige un motif.</p>
      </section>
      {err && <p className="erreur">{err}</p>}
      {msg && <p className="meta" style={{ color: "var(--green)" }}>{msg}</p>}

      <div className="grid grid-2">
        <article className="card">
          <h2>File d’événements ({file.length})</h2>
          {file.length === 0 && <p className="empty">Rien en attente. C’est le bon état.</p>}
          <ul className="timeline">
            {file.map((e) => (
              <li key={e.id}>
                <div>
                  Match #{e.match_id} · {e.minute}′ · {e.type} · {e.equipe_concernee}
                </div>
                <div style={{ display: "flex", gap: "0.4rem", marginTop: "0.45rem" }}>
                  <button className="btn btn-ghost" type="button" onClick={() => valider(e.id)}>Valider</button>
                  <button className="btn btn-danger" type="button" onClick={() => rejeter(e.id)}>Rejeter</button>
                  <Link className="btn btn-ghost" to={`/orga/matchs/${e.match_id}`}>Match</Link>
                </div>
              </li>
            ))}
          </ul>
        </article>
        <article className="card">
          <h2>Matchs de la saison</h2>
          {matchs.map((m) => (
            <Link key={m.id} to={`/orga/matchs/${m.id}`} className="match">
              <div className="team">
                {clubName(clubsById, m.equipe_domicile_id)}
                <div className="meta">{m.journee} · <span className={`badge ${m.statut === "valide" ? "ok" : "wait"}`}>{STATUT[m.statut] || m.statut}</span></div>
              </div>
              <div className="score">{m.score_domicile}–{m.score_exterieur}</div>
              <div className="team right">{clubName(clubsById, m.equipe_exterieur_id)}</div>
            </Link>
          ))}
        </article>
      </div>
    </div>
  );
}
