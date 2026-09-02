import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, clearTokens } from "../api.js";
import Chrono, { elapsed } from "../components/Chrono.jsx";
import { clubName, useKivu } from "../context.jsx";
import { stripDemo } from "../display.js";

const LABELS = {
  but: "But",
  carton_jaune: "Carton jaune",
  carton_rouge: "Carton rouge",
  but_contre_son_camp: "CSC",
  penalty: "Penalty",
  remplacement: "Changement",
  passe_decisive: "Passe",
};

export default function OrgaMatch() {
  const { id } = useParams();
  const nav = useNavigate();
  const { clubsById } = useKivu();
  const [match, setMatch] = useState(null);
  const [evts, setEvts] = useState([]);
  const [joueurs, setJoueurs] = useState([]);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [type, setType] = useState("but");
  const [cote, setCote] = useState("domicile");
  const [joueurId, setJoueurId] = useState("");
  const [minute, setMinute] = useState("0");

  const home = stripDemo(clubName(clubsById, match?.equipe_domicile_id));
  const away = stripDemo(clubName(clubsById, match?.equipe_exterieur_id));

  async function load() {
    try {
      const [m, e] = await Promise.all([api.matchGestion(id), api.evenementsStaff(id)]);
      setMatch(m);
      setEvts(e || []);
      const clubId = cote === "exterieur" ? m.equipe_exterieur_id : m.equipe_domicile_id;
      const js = await api.joueurs(clubId).catch(() => []);
      setJoueurs(js || []);
    } catch (ex) {
      setErr(ex.message);
      if (ex.status === 401) {
        clearTokens();
        nav("/login", { replace: true });
      }
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (!match) return;
    const clubId = cote === "exterieur" ? match.equipe_exterieur_id : match.equipe_domicile_id;
    api.joueurs(clubId).then((js) => {
      setJoueurs(js || []);
      setJoueurId("");
    }).catch(() => setJoueurs([]));
  }, [cote, match]);

  const running = match?.statut === "en_cours";
  const liveMin = useMemo(() => {
    if (!match?.started_at) return 0;
    return elapsed(match.started_at, match.ended_at, Date.now()).min;
  }, [match]);

  useEffect(() => {
    if (running) setMinute(String(liveMin));
  }, [running, liveMin]);

  async function act(fn, ok) {
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      await fn();
      setMsg(ok);
      await load();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  function demarrer() {
    return act(() => api.changerStatut(id, "en_cours"), "Match démarré. Le chrono tourne.");
  }
  function terminer() {
    return act(() => api.changerStatut(id, "termine"), "Match terminé. Le chrono est arrêté.");
  }
  function publier() {
    return act(() => api.validerMatch(id), "Match validé. Classement et site public à jour.");
  }

  async function ajouter(e) {
    e.preventDefault();
    if (!joueurId) {
      setErr("Choisissez un joueur.");
      return;
    }
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      await api.saisirEvenement(id, {
        temp_id: crypto.randomUUID(),
        minute: Number.parseInt(String(minute), 10) || 0,
        type,
        joueur_id: Number(joueurId),
        equipe_concernee: cote,
      });
      setMsg(type === "but" ? "But enregistré. Le score a changé." : "Carton enregistré.");
      await load();
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  if (!match) return <p className="empty">Chargement…</p>;

  return (
    <div className="shell">
      <p className="kicker" style={{ paddingTop: "1rem" }}>
        <Link to="/orga">← Organisateur</Link>
      </p>
      <section className="hero">
        <p className="kicker">{match.journee} · {match.statut}</p>
        <h1>{home} {match.score_domicile}–{match.score_exterieur} {away}</h1>
        {match.statut === "en_cours" && (
          <p className="live-now" style={{ marginTop: "0.6rem" }}>
            <span className="live-dot" aria-hidden="true"><b /></span>
            En cours
          </p>
        )}
        {(match.statut === "en_cours" || match.statut === "termine") && match.started_at && (
          <Chrono
            startedAt={match.started_at}
            endedAt={match.ended_at}
            running={match.statut === "en_cours"}
          />
        )}
      </section>
      {err && <p className="erreur">{err}</p>}
      {msg && <p className="empty">{msg}</p>}

      <div className="orga-actions">
        {match.statut === "programme" && (
          <button className="btn btn-primary" type="button" disabled={busy} onClick={demarrer}>
            Démarrer le match
          </button>
        )}
        {match.statut === "en_cours" && (
          <button className="btn" type="button" disabled={busy} onClick={terminer}>
            Terminer le match
          </button>
        )}
        {match.statut === "termine" && !match.locked && (
          <button className="btn btn-primary" type="button" disabled={busy} onClick={publier}>
            Valider le match
          </button>
        )}
        {match.locked && <p className="empty">Match verrouillé — plus aucune modification.</p>}
      </div>

      {match.statut === "en_cours" && (
        <form className="compte-form" onSubmit={ajouter} style={{ marginTop: "1.2rem" }}>
          <p className="kicker">Ajouter un événement</p>
          <label className="field">
            Type
            <select value={type} onChange={(e) => setType(e.target.value)}>
              <option value="but">But</option>
              <option value="carton_jaune">Carton jaune</option>
            </select>
          </label>
          <label className="field">
            Équipe
            <select value={cote} onChange={(e) => setCote(e.target.value)}>
              <option value="domicile">{home}</option>
              <option value="exterieur">{away}</option>
            </select>
          </label>
          <label className="field">
            Joueur
            <select value={joueurId} onChange={(e) => setJoueurId(e.target.value)} required>
              <option value="">—</option>
              {joueurs.map((j) => (
                <option key={j.id} value={j.id}>{j.nom_complet}</option>
              ))}
            </select>
          </label>
          <label className="field">
            Minute
            <input
              type="number"
              min="0"
              max="130"
              step="1"
              value={minute}
              onChange={(e) => setMinute(e.target.value)}
              required
            />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy}>
            Enregistrer
          </button>
        </form>
      )}

      <div className="section-head">
        <h2>Feuille</h2>
      </div>
      {evts.length === 0 && <p className="empty">Aucun événement.</p>}
      <ul className="timeline">
        {evts.map((e) => (
          <li key={e.id}>
            {e.minute}′ · {LABELS[e.type] || e.type} · {e.equipe_concernee} · {e.statut_validation}
          </li>
        ))}
      </ul>
    </div>
  );
}
