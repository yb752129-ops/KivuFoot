import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, clearTokens } from "../api.js";
import { clubName, useKivu } from "../context.jsx";
import { stripDemo } from "../display.js";

const STATUT = {
  programme: "Programmé",
  en_cours: "En cours",
  termine: "Terminé",
  valide: "Validé",
  conteste: "Contesté",
};

export default function Orga() {
  const nav = useNavigate();
  const { saison, clubs, clubsById } = useKivu();
  const [me, setMe] = useState(null);
  const [file, setFile] = useState([]);
  const [matchs, setMatchs] = useState([]);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

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

  function nom(id) {
    return stripDemo(clubName(clubsById, id));
  }

  async function preparerTest() {
    setBusy(true);
    setErr("");
    try {
      const kadutu = clubs.find((c) => /kadutu/i.test(c.nom));
      const ibanda = clubs.find((c) => /ibanda/i.test(c.nom));
      if (!kadutu || !ibanda || !saison) throw new Error("Clubs DEMO introuvables.");
      const deja = matchs.find(
        (m) =>
          m.statut === "programme" &&
          ((m.equipe_domicile_id === kadutu.id && m.equipe_exterieur_id === ibanda.id) ||
            (m.equipe_domicile_id === ibanda.id && m.equipe_exterieur_id === kadutu.id)),
      );
      if (deja) {
        nav(`/orga/matchs/${deja.id}`);
        return;
      }
      const m = await api.creerMatch({
        saison_id: saison.id,
        journee: "TEST",
        date_heure: new Date().toISOString(),
        stade: kadutu.stade || "Stade Kadutu",
        equipe_domicile_id: kadutu.id,
        equipe_exterieur_id: ibanda.id,
      });
      nav(`/orga/matchs/${m.id}`);
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    clearTokens();
    nav("/", { replace: true });
  }

  return (
    <div className="shell">
      <p className="kicker" style={{ paddingTop: "1rem" }}>
        {me?.nom_complet || me?.email} ·{" "}
        <button className="linkish" type="button" onClick={logout}>Déconnexion</button>
      </p>
      <section className="hero">
        <h1>Organisateur</h1>
        <p className="lead">Démarrer, saisir, terminer, valider. Rien n’est officiel avant validation.</p>
      </section>
      {err && <p className="erreur">{err}</p>}
      {msg && <p className="empty">{msg}</p>}

      <p>
        <button className="btn btn-primary" type="button" disabled={busy} onClick={preparerTest}>
          {busy ? "…" : "Match test · Kadutu — Ibanda"}
        </button>
      </p>

      <div className="section-head">
        <h2>File d’événements ({file.length})</h2>
      </div>
      {file.length === 0 && <p className="empty">Rien en attente.</p>}
      <ul className="timeline">
        {file.map((e) => (
          <li key={e.id}>
            Match #{e.match_id} · {e.minute}′ · {e.type}
            {" · "}
            <Link to={`/orga/matchs/${e.match_id}`}>Ouvrir</Link>
          </li>
        ))}
      </ul>

      <div className="section-head">
        <h2>Matchs</h2>
      </div>
      <div className="sheet">
        {matchs.map((m) => (
          <Link key={m.id} to={`/orga/matchs/${m.id}`} className="scoreboard">
            <div className="sb-line">
              <span className="sb-name">{nom(m.equipe_domicile_id)}</span>
              <span className="sb-score">
                {m.score_domicile}<span className="sb-dash">–</span>{m.score_exterieur}
              </span>
              <span className="sb-name away">{nom(m.equipe_exterieur_id)}</span>
            </div>
            <div className="sb-meta">
              <span className="sb-meta-journee">{STATUT[m.statut] || m.statut}</span>
              <span className="sb-meta-lieu">{m.journee}</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
