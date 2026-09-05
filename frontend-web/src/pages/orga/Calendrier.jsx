import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api } from "../../api.js";
import { useAuth } from "../../auth.jsx";
import { useKivu } from "../../context.jsx";
import { stripDemo } from "../../display.js";
import { AVenirLigne } from "../../components/LignesMatch.jsx";
import { assurerSaison, isoDepuisDateHeure } from "./saison.js";

export default function OrgaCalendrier() {
  const { user } = useAuth();
  const {
    saison, saisonClubs, clubsById, competition,
    rechargerCompetitions, choisirCompetition, chargerClubsSaison,
  } = useKivu();
  const bureau = user?.role === "organisateur" || user?.role === "admin";
  const equipes = saisonClubs ?? [];
  const [matchs, setMatchs] = useState([]);
  const [domId, setDomId] = useState("");
  const [extId, setExtId] = useState("");
  const [dateMatch, setDateMatch] = useState("");
  const [heureMatch, setHeureMatch] = useState("");
  const [stadeMatch, setStadeMatch] = useState("");
  const [journee, setJournee] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  async function load() {
    if (!saison) {
      setMatchs([]);
      return;
    }
    const ms = await api.matchsGestion(saison.id).catch(() => []);
    setMatchs(ms || []);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [saison]);

  if (!bureau) return <Navigate to="/orga/matchs" replace />;

  async function programmer(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      const s = await assurerSaison({
        saison, competition, api, rechargerCompetitions, choisirCompetition, chargerClubsSaison,
      });
      const d = Number(domId);
      const x = Number(extId);
      if (!d || !x) throw new Error("Choisissez les deux équipes.");
      if (d === x) throw new Error("Une équipe ne peut pas jouer contre elle-même.");
      const domicile = equipes.find((c) => c.id === d) || clubsById[d];
      await api.creerMatch({
        saison_id: s.id,
        journee: journee.trim().slice(0, 20) || null,
        date_heure: isoDepuisDateHeure(dateMatch, heureMatch),
        stade: stadeMatch.trim() || domicile?.stade || null,
        equipe_domicile_id: d,
        equipe_exterieur_id: x,
      });
      setMsg("Match programmé. Il apparaît dans À venir côté public.");
      setDomId("");
      setExtId("");
      setStadeMatch("");
      setJournee("");
      await load();
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  const aVenir = matchs
    .filter((m) => m.statut === "programme")
    .sort((a, b) => new Date(a.date_heure) - new Date(b.date_heure));

  return (
    <section className="hero">
      <h1>Calendrier</h1>
      <p className="lead">Un match programmé doit se voir sur l’Accueil public.</p>
      {err && <p className="erreur">{err}</p>}
      {msg && <p className="empty">{msg}</p>}

      {equipes.length < 2 ? (
        <p className="empty">Inscrivez au moins deux équipes. <Link to="/orga/equipes">Équipes</Link></p>
      ) : (
        <form className="compte-form" onSubmit={programmer}>
          <label className="field">
            Domicile
            <select value={domId} onChange={(e) => setDomId(e.target.value)} required>
              <option value="">—</option>
              {equipes.map((c) => (
                <option key={c.id} value={c.id}>{stripDemo(c.nom)}</option>
              ))}
            </select>
          </label>
          <label className="field">
            Extérieur
            <select value={extId} onChange={(e) => setExtId(e.target.value)} required>
              <option value="">—</option>
              {equipes.map((c) => (
                <option key={c.id} value={c.id}>{stripDemo(c.nom)}</option>
              ))}
            </select>
          </label>
          <div className="comp-grid">
            <label className="field">
              Date
              <input type="date" value={dateMatch} onChange={(e) => setDateMatch(e.target.value)} required />
            </label>
            <label className="field">
              Heure
              <input type="time" value={heureMatch} onChange={(e) => setHeureMatch(e.target.value)} required />
            </label>
          </div>
          <label className="field">
            Stade
            <input
              value={stadeMatch}
              onChange={(e) => setStadeMatch(e.target.value)}
              placeholder={equipes.find((c) => String(c.id) === String(domId))?.stade || "à compléter"}
            />
          </label>
          <label className="field">
            Journée
            <input value={journee} onChange={(e) => setJournee(e.target.value)} maxLength={20} placeholder="ex. J1" />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "…" : "Programmer le match"}
          </button>
        </form>
      )}

      <div className="section-head">
        <h2>À venir</h2>
      </div>
      {aVenir.length === 0 && <p className="empty">Aucun match programmé.</p>}
      {aVenir.map((m) => (
        <AVenirLigne key={m.id} match={m} clubsById={clubsById} to={`/orga/matchs/${m.id}`} />
      ))}
    </section>
  );
}
