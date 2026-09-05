import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api.js";
import { formatMinute, labelEvenement } from "../../display.js";

export default function AdminVue() {
  const [file, setFile] = useState([]);
  const [props, setProps] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.fileValidation().then(setFile).catch((e) => setErr(e.message));
    api.propositions().then(setProps).catch(() => setProps([]));
  }, []);

  const nAttente = file.length;
  const nProps = (props || []).filter((p) => p.statut === "en_attente").length;

  return (
    <section className="hero">
      <p className="kicker">Administration</p>
      <h1>Plateforme</h1>
      <p className="lead">L’audit et les propositions. Le public ne voit pas ça. L’organisateur tient la compétition.</p>
      {err && <p className="erreur">{err}</p>}

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
