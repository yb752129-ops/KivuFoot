import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, clearTokens } from "../api.js";
import { clubName, useKivu } from "../context.jsx";

export default function OrgaMatch() {
  const { id } = useParams();
  const nav = useNavigate();
  const { clubsById } = useKivu();
  const [match, setMatch] = useState(null);
  const [evts, setEvts] = useState([]);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      const [m, e] = await Promise.all([api.matchGestion(id), api.evenementsStaff(id)]);
      setMatch(m);
      setEvts(e);
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

  async function publier() {
    setBusy(true);
    setErr("");
    try {
      await api.validerMatch(id);
      setMsg("Match publié. Il apparaît maintenant sur le site public.");
      await load();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (!match) return <p className="empty">Chargement…</p>;

  const enAttente = evts.filter((e) => e.statut_validation === "en_attente").length;

  return (
    <div className="shell">
      <p><Link to="/orga">← Tableau de bord</Link></p>
      <section className="hero">
        <div className="kicker">{match.journee} · {match.statut}</div>
        <h1>
          {clubName(clubsById, match.equipe_domicile_id)} {match.score_domicile}–{match.score_exterieur}{" "}
          {clubName(clubsById, match.equipe_exterieur_id)}
        </h1>
      </section>
      {err && <p className="erreur">{err}</p>}
      {msg && <p className="meta" style={{ color: "var(--green)" }}>{msg}</p>}
      <div className="card">
        <h2>Événements</h2>
        <ul className="timeline">
          {evts.map((e) => (
            <li key={e.id}>
              {e.minute}′ · {e.type} · {e.equipe_concernee} · {e.statut_validation}
            </li>
          ))}
        </ul>
        {!match.locked && (
          <button className="btn btn-primary" type="button" disabled={busy || enAttente > 0} onClick={publier}>
            {enAttente > 0 ? `Encore ${enAttente} événement(s) en attente` : "Publier ce match"}
          </button>
        )}
        {match.locked && <p className="meta">Match verrouillé — plus aucune modification.</p>}
      </div>
    </div>
  );
}
