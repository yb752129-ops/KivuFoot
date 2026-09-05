import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api.js";
import { useKivu } from "../../context.jsx";
import { formatMinute, labelEvenement, stripDemo } from "../../display.js";

const TYPE_LIBELLE = {
  championnat: "Championnat",
  coupe: "Coupe",
  tournoi: "Tournoi",
};

export default function AdminVue() {
  const { competitions, competition, choisirCompetition, rechargerCompetitions } = useKivu();
  const [file, setFile] = useState([]);
  const [props, setProps] = useState([]);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(0);

  useEffect(() => {
    api.fileValidation().then(setFile).catch((e) => setErr(e.message));
    api.propositions().then(setProps).catch(() => setProps([]));
  }, []);

  const nAttente = file.length;
  const nProps = (props || []).filter((p) => p.statut === "en_attente").length;

  async function supprimer(c) {
    const nom = c.est_demo ? `Démo — ${stripDemo(c.nom)}` : stripDemo(c.nom);
    if (!window.confirm(`Supprimer « ${nom} » (#${c.id}) ? Les matchs déjà joués bloquent la suppression. Les clubs restent.`)) {
      return;
    }
    setBusy(c.id);
    setErr("");
    setMsg("");
    try {
      await api.supprimerCompetition(c.id);
      const list = await rechargerCompetitions();
      if (competition?.id === c.id) {
        const next = (list || []).find((x) => x.id !== c.id);
        await choisirCompetition(next?.id, list || []);
      }
      setMsg("Compétition supprimée.");
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(0);
    }
  }

  return (
    <section className="hero">
      <p className="kicker">Administration</p>
      <h1>Plateforme</h1>
      <p className="lead">L’audit et les propositions. Le public ne voit pas ça. L’organisateur tient la compétition.</p>
      {err && <p className="erreur">{err}</p>}
      {msg && <p className="empty">{msg}</p>}

      <div className="orga-chiffres">
        <div className="orga-chiffre stamp">
          <strong>{nAttente}</strong>
          <span>À valider</span>
        </div>
        <Link to="/admin/propositions" className="orga-chiffre stamp">
          <strong>{nProps}</strong>
          <span>Propositions</span>
        </Link>
      </div>

      <div className="section-head">
        <h2>En attente de validation</h2>
      </div>
      {nAttente === 0 && <p className="empty">Rien en attente.</p>}
      {file.slice(0, 12).map((e) => (
        <p key={e.id} className="orga-alerte">
          {formatMinute(e.minute, e.minute_additionnelle)} · {labelEvenement(e)}
          {" · "}
          <Link to={`/orga/matchs/${e.match_id}`}>Ouvrir le match</Link>
        </p>
      ))}

      <div className="section-head">
        <h2>Compétitions</h2>
      </div>
      {(competitions || []).length === 0 && <p className="empty">Aucune compétition.</p>}
      {(competitions || []).map((c) => (
        <div key={c.id} className="avenir-row">
          <span className="avenir-noms">
            <span>{c.est_demo ? `Démo — ${stripDemo(c.nom)}` : stripDemo(c.nom)}</span>
            <span className="meta-line">
              #{c.id} · {TYPE_LIBELLE[c.type] || c.type}
            </span>
          </span>
          <button
            className="linkish"
            type="button"
            disabled={busy === c.id}
            onClick={() => supprimer(c)}
          >
            {busy === c.id ? "…" : "Supprimer"}
          </button>
        </div>
      ))}

      <div className="sheet" style={{ marginTop: "1.4rem" }}>
        <Link to="/orga" className="avenir-row">
          <span className="avenir-noms">
            <span>Organisation</span>
            <span className="meta-line">/orga — la compétition</span>
          </span>
        </Link>
        <Link to="/collecteur" className="avenir-row">
          <span className="avenir-noms">
            <span>Collecte</span>
            <span className="meta-line">/collecteur — la saisie</span>
          </span>
        </Link>
      </div>
    </section>
  );
}
