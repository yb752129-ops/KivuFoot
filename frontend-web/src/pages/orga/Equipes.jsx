import { useMemo, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { api } from "../../api.js";
import { useAuth } from "../../auth.jsx";
import { useKivu } from "../../context.jsx";
import { stripDemo } from "../../display.js";
import { assurerSaison } from "./saison.js";

export default function OrgaEquipes() {
  const { user } = useAuth();
  const nav = useNavigate();
  const {
    saison, saisonClubs, competition,
    rechargerClubs, chargerClubsSaison, rechargerCompetitions, choisirCompetition,
  } = useKivu();
  const bureau = user?.role === "organisateur" || user?.role === "admin";
  const [q, setQ] = useState("");
  const [nom, setNom] = useState("");
  const [ville, setVille] = useState("");
  const [stade, setStade] = useState("");
  const [ouvert, setOuvert] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const list = useMemo(() => {
    const rows = saisonClubs ?? [];
    const n = q.trim().toLowerCase();
    if (!n) return rows;
    return rows.filter((c) =>
      stripDemo(c.nom).toLowerCase().includes(n) || (c.ville || "").toLowerCase().includes(n),
    );
  }, [saisonClubs, q]);

  if (!bureau) return <Navigate to="/orga/matchs" replace />;

  async function creer(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const s = await assurerSaison({
        saison, competition, api, rechargerCompetitions, choisirCompetition, chargerClubsSaison,
      });
      if (!nom.trim() || !ville.trim()) throw new Error("Nom et ville / département sont obligatoires.");
      const club = await api.creerClub({ nom: nom.trim(), ville: ville.trim(), stade: stade.trim() || null });
      await api.inscrireClub(s.id, club.id);
      await rechargerClubs();
      await chargerClubsSaison(s.id);
      setNom("");
      setVille("");
      setStade("");
      setOuvert(false);
      nav(`/orga/equipes/${club.id}`);
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="hero">
      <div className="section-head" style={{ marginTop: 0 }}>
        <h1 style={{ margin: 0 }}>Équipes</h1>
        <button className="linkish" type="button" onClick={() => setOuvert((v) => !v)}>
          {ouvert ? "Fermer" : "Nouvelle équipe"}
        </button>
      </div>
      {err && <p className="erreur">{err}</p>}
      <label className="field">
        Rechercher
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nom ou ville" />
      </label>
      {ouvert && (
        <form className="compte-form" onSubmit={creer}>
          <label className="field">
            Nom de l’équipe
            <input value={nom} onChange={(e) => setNom(e.target.value)} placeholder="à compléter" required />
          </label>
          <label className="field">
            Ville / département
            <input value={ville} onChange={(e) => setVille(e.target.value)} placeholder="à compléter" required />
          </label>
          <label className="field">
            Stade
            <input value={stade} onChange={(e) => setStade(e.target.value)} placeholder="à compléter" />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "…" : "Inscrire l’équipe"}
          </button>
        </form>
      )}
      {list.length === 0 && <p className="empty">Aucune équipe inscrite.</p>}
      {list.map((c) => (
        <Link key={c.id} to={`/orga/equipes/${c.id}`} className="avenir-row">
          <span className="club-initiale" aria-hidden="true">{(stripDemo(c.nom) || "?").charAt(0)}</span>
          <span className="avenir-noms">
            <span>{stripDemo(c.nom)}</span>
            <span className="meta-line">{[c.ville, c.stade].filter(Boolean).join(" — ") || "à compléter"}</span>
          </span>
        </Link>
      ))}
    </section>
  );
}
