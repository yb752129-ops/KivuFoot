import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api.js";
import { useAuth } from "../../auth.jsx";
import { clubName, useKivu } from "../../context.jsx";
import { stripDemo } from "../../display.js";

export default function CoachMatch() {
  const { id } = useParams();
  const { user } = useAuth();
  const { clubsById } = useKivu();
  const clubId = user?.club_id;
  const [match, setMatch] = useState(null);
  const [joueurs, setJoueurs] = useState([]);
  const [autresJoueurs, setAutresJoueurs] = useState([]);
  const [parts, setParts] = useState([]);
  const [draft, setDraft] = useState({});
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const m = await api.match(id);
    setMatch(m);
    const otherId = clubId === m.equipe_domicile_id ? m.equipe_exterieur_id : m.equipe_domicile_id;
    const [js, autres, p] = await Promise.all([
      clubId ? api.joueurs(clubId).catch(() => []) : [],
      otherId ? api.joueurs(otherId).catch(() => []) : [],
      api.participations(id).catch(() => []),
    ]);
    setJoueurs(js || []);
    setAutresJoueurs(autres || []);
    setParts(p || []);
    const d = {};
    (p || []).forEach((x) => {
      if (x.club_id === clubId) d[x.joueur_id] = x.statut;
    });
    setDraft(d);
  }

  useEffect(() => {
    if (!clubId) return;
    load().catch((e) => setErr(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, clubId]);

  if (!clubId) return <p className="empty">Aucun club rattaché.</p>;
  if (!match) return <p className="empty">{err || "Chargement…"}</p>;

  const home = stripDemo(clubName(clubsById, match.equipe_domicile_id));
  const away = stripDemo(clubName(clubsById, match.equipe_exterieur_id));
  const cote = clubId === match.equipe_domicile_id ? "domicile" : "exterieur";
  const moi = cote === "domicile" ? home : away;
  const locked = match.locked || match.statut === "valide";

  function cycle(jid) {
    if (locked) return;
    setDraft((d) => {
      const cur = d[jid];
      const next = cur === "titulaire" ? "remplacant" : cur === "remplacant" ? "" : "titulaire";
      const copy = { ...d };
      if (!next) delete copy[jid];
      else copy[jid] = next;
      return copy;
    });
  }

  function badge(jid) {
    const st = draft[jid];
    if (st === "titulaire") return "Titu";
    if (st === "remplacant") return "Banc";
    return "—";
  }

  async function enregistrer() {
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      const mine = parts.filter((p) => p.club_id === clubId);
      const byJoueur = Object.fromEntries(mine.map((p) => [p.joueur_id, p]));
      for (const j of joueurs) {
        const want = draft[j.id];
        const have = byJoueur[j.id];
        if (!want && have) {
          await api.retirerParticipation(id, have.id);
        } else if (want && !have) {
          await api.ajouterParticipation(id, {
            joueur_id: j.id,
            club_id: clubId,
            equipe_concernee: cote,
            statut: want,
            minute_entree: 0,
          });
        } else if (want && have && have.statut !== want) {
          await api.modifierParticipation(id, have.id, { statut: want });
        }
      }
      setMsg("Composition enregistrée.");
      await load();
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  const autreCote = cote === "domicile" ? "exterieur" : "domicile";
  const autreParts = parts.filter((p) => p.equipe_concernee === autreCote);
  const autreNom = cote === "domicile" ? away : home;

  return (
    <section className="hero">
      <p className="kicker"><Link to="/coach/matchs">← Matchs</Link></p>
      <h1>{home} · {away}</h1>
      <p className="lead">Votre équipe seulement : {moi}. Toucher un nom : titulaire, banc, ou rien.</p>
      {err && <p className="erreur">{err}</p>}
      {msg && <p className="empty">{msg}</p>}
      {locked && <p className="empty">Match verrouillé — plus aucune modification.</p>}

      <div className="section-head">
        <h2>{moi}</h2>
      </div>
      {joueurs.length === 0 && <p className="empty">Aucun joueur dans l’effectif. L’effectif se tient au club.</p>}
      {joueurs.map((j) => (
        <button
          key={j.id}
          type="button"
          className="comp-row"
          disabled={locked || busy}
          onClick={() => cycle(j.id)}
        >
          <span>{j.nom_complet}</span>
          <strong>{badge(j.id)}</strong>
        </button>
      ))}
      {!locked && (
        <button className="btn btn-primary" type="button" disabled={busy} onClick={enregistrer} style={{ marginTop: "0.8rem" }}>
          {busy ? "…" : "Enregistrer la composition"}
        </button>
      )}

      <div className="section-head">
        <h2>{autreNom}</h2>
      </div>
      <p className="lead">L’autre composition. Vous ne la posez pas.</p>
      {autreParts.length === 0 && <p className="empty">Composition à compléter</p>}
      {autreParts.map((p) => {
        const j = autresJoueurs.find((x) => x.id === p.joueur_id);
        return (
          <div key={p.id} className="comp-row">
            <span>{j?.nom_complet || "à compléter"}</span>
            <strong>{p.statut === "titulaire" ? "Titu" : "Banc"}</strong>
          </div>
        );
      })}

      <p className="id-out">
        <Link to={`/matchs/${id}`}>Voir le match public</Link>
      </p>
    </section>
  );
}
