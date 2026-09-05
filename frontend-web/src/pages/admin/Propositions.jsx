import { useEffect, useState } from "react";
import { api } from "../../api.js";
import { clubName, useKivu } from "../../context.jsx";
import { labelPoste, stripDemo } from "../../display.js";

const CHAMP_LIBELLE = {
  nom_complet: "Nom",
  date_naissance: "Naissance",
  poste: "Poste",
  club_actuel_id: "Club",
};

export default function AdminPropositions() {
  const { clubsById } = useKivu();
  const [rows, setRows] = useState([]);
  const [joueurs, setJoueurs] = useState([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(0);

  async function load() {
    const [ps, js] = await Promise.all([api.propositions(), api.joueurs()]);
    setRows(ps || []);
    setJoueurs(js || []);
  }

  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, []);

  const byId = Object.fromEntries((joueurs || []).map((j) => [j.id, j]));

  function valeur(champ, v) {
    if (v == null || v === "") return "—";
    if (champ === "poste") return labelPoste(v) || v;
    if (champ === "club_actuel_id") {
      const n = stripDemo(clubName(clubsById, Number(v)));
      return n && n !== "—" ? n : v;
    }
    return String(v);
  }

  async function approuver(id) {
    setBusy(id);
    setErr("");
    try {
      await api.approuverProposition(id);
      await load();
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(0);
    }
  }

  const attente = (rows || []).filter((p) => p.statut === "en_attente");

  return (
    <section className="hero">
      <p className="kicker">Administration</p>
      <h1>Propositions</h1>
      <p className="lead">Le club propose. Ici on approuve. Pas de fusion automatique.</p>
      {err && <p className="erreur">{err}</p>}
      {attente.length === 0 && !err && <p className="empty">Rien en attente.</p>}
      {attente.map((p) => {
        const j = byId[p.joueur_id];
        return (
          <div key={p.id} className="orga-alerte">
            <p className="avenir-noms" style={{ margin: 0 }}>
              <span>{j?.nom_complet || `Joueur #${p.joueur_id}`}</span>
              <span className="meta-line">
                {CHAMP_LIBELLE[p.champ] || p.champ}
                {" : "}
                {valeur(p.champ, p.ancienne_valeur)}
                {" → "}
                {valeur(p.champ, p.nouvelle_valeur)}
              </span>
            </p>
            <p style={{ margin: "0.35rem 0 0" }}>
              <button
                className="linkish"
                type="button"
                disabled={busy === p.id}
                onClick={() => approuver(p.id)}
              >
                {busy === p.id ? "…" : "Approuver"}
              </button>
            </p>
          </div>
        );
      })}
    </section>
  );
}
