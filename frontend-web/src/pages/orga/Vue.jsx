import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api } from "../../api.js";
import { useAuth } from "../../auth.jsx";
import { useKivu } from "../../context.jsx";
import { formatMinute, labelEvenement, stripDemo } from "../../display.js";

export default function OrgaVue() {
  const { user } = useAuth();
  const { competition, saison, saisonClubs, choisirCompetition, rechargerCompetitions } = useKivu();
  const bureau = user?.role === "organisateur" || user?.role === "admin";
  const [matchs, setMatchs] = useState([]);
  const [file, setFile] = useState([]);
  const [effectifs, setEffectifs] = useState(null);
  const [nomComp, setNomComp] = useState("");
  const [typeComp, setTypeComp] = useState("tournoi");
  const [nomSaison, setNomSaison] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (!bureau) return;
    api.fileValidation().then(setFile).catch(() => setFile([]));
  }, [bureau]);

  useEffect(() => {
    if (!bureau || !saison) {
      setEffectifs(null);
      return;
    }
    // Le total vient des résumés d'effectifs de la saison, sans la limite
    // publique de 100 joueurs de /joueurs?limit=100.
    api.effectifsSaison(saison.id).then(setEffectifs).catch(() => setEffectifs(null));
  }, [bureau, saison]);

  useEffect(() => {
    if (!saison) {
      setMatchs([]);
      return;
    }
    api.matchsGestion(saison.id).then(setMatchs).catch(() => setMatchs([]));
  }, [saison]);

  if (!bureau) return <Navigate to="/orga/matchs" replace />;

  const equipes = saisonClubs ?? [];
  const nJoueurs = effectifs
    ? effectifs.reduce((total, ligne) => total + Number(ligne.total_joueurs || 0), 0)
    : null;
  const nProg = matchs.filter((m) => m.statut === "programme").length;
  const nLive = matchs.filter((m) => m.statut === "en_cours").length;
  const nAttente = file.length;

  async function creer(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      const nom = nomComp.trim();
      if (!nom) throw new Error("Indiquez le nom de la compétition.");
      const comp = await api.creerCompetition({
        nom,
        type: typeComp,
        saison_label: nomSaison.trim() || null,
        est_demo: false,
      });
      await api.creerSaison({
        competition_id: comp.id,
        nom: nomSaison.trim() || null,
        club_ids: [],
      });
      const list = await rechargerCompetitions();
      await choisirCompetition(comp.id, list || []);
      setMsg("Compétition créée.");
      setNomComp("");
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="hero">
      <p className="kicker">Organisateur</p>
      <h1>{competition ? stripDemo(competition.nom) : "Compétition"}</h1>
      <p className="lead">Tenir la compétition. Le public regarde. Le collecteur écrit le match.</p>
      {err && <p className="erreur">{err}</p>}
      {msg && <p className="empty">{msg}</p>}

      <div className="orga-chiffres">
        <Link to="/orga/equipes" className="orga-chiffre">
          <strong>{equipes.length}</strong>
          <span>Équipes</span>
        </Link>
        <Link to="/orga/equipes" className="orga-chiffre" title="Total exact des effectifs des équipes inscrites à cette édition">
          <strong>{nJoueurs === null ? "—" : nJoueurs}</strong>
          <span>Joueurs inscrits</span>
        </Link>
        <Link to="/orga/calendrier" className="orga-chiffre">
          <strong>{nProg}</strong>
          <span>À venir</span>
        </Link>
        <Link to="/orga/matchs" className="orga-chiffre">
          <strong>{nLive}</strong>
          <span>En cours</span>
        </Link>
      </div>

      <div className="section-head">
        <h2>À valider ({nAttente})</h2>
      </div>
      {nAttente === 0 && <p className="empty">Rien en attente.</p>}
      {file.slice(0, 8).map((e) => (
        <p key={e.id} className="orga-alerte">
          {formatMinute(e.minute, e.minute_additionnelle)} · {labelEvenement(e)}
          {" · "}
          <Link to={`/orga/matchs/${e.match_id}`}>Ouvrir le match</Link>
        </p>
      ))}

      <details className="orga-autre">
        <summary>Autre compétition</summary>
        <form className="compte-form" onSubmit={creer}>
          <label className="field">
            Nom
            <input value={nomComp} onChange={(e) => setNomComp(e.target.value)} required />
          </label>
          <label className="field">
            Type
            <select value={typeComp} onChange={(e) => setTypeComp(e.target.value)}>
              <option value="tournoi">Tournoi</option>
              <option value="championnat">Championnat</option>
              <option value="coupe">Coupe</option>
            </select>
          </label>
          <label className="field">
            Saison / édition
            <input value={nomSaison} onChange={(e) => setNomSaison(e.target.value)} placeholder="ex. 2e semestre 2026" />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "…" : "Créer la compétition"}
          </button>
        </form>
      </details>
    </section>
  );
}
