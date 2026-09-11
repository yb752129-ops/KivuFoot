import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../../api.js";
import { useKivu } from "../../context.jsx";
import { labelPoste, stripDemo } from "../../display.js";

const FORMATIONS = ["4-4-2", "4-3-3", "3-5-2", "5-3-2"];

export default function Composition() {
  const { matchId } = useParams();
  const { clubsById } = useKivu();
  const [moi, setMoi] = useState(null);
  const [match, setMatch] = useState(null);
  const [compo, setCompo] = useState(null);
  const [joueurs, setJoueurs] = useState([]);
  const [staff, setStaff] = useState([]);
  const [choix, setChoix] = useState({});
  const [formation, setFormation] = useState("");
  const [staffId, setStaffId] = useState("");
  const [msg, setMsg] = useState("");
  const [erreur, setErreur] = useState("");

  useEffect(() => {
    api.me().then(setMoi).catch(() => setMoi(null));
    api.match(matchId).then(setMatch).catch(() => setMatch(null));
    api.composition(matchId).then(setCompo).catch(() => setCompo(null));
  }, [matchId]);

  const clubId = moi?.club_id ?? null;
  const equipe = match ? (match.equipe_domicile_id === clubId ? "domicile" : match.equipe_exterieur_id === clubId ? "exterieur" : null) : null;

  useEffect(() => {
    if (!clubId) return;
    api.joueurs(clubId).then(setJoueurs).catch(() => setJoueurs([]));
    api.staffClub(clubId).then(setStaff).catch(() => setStaff([]));
  }, [clubId]);

  useEffect(() => {
    if (!compo || !equipe) return;
    const bloc = compo[equipe];
    const c = {};
    (bloc.titulaires || []).forEach((j) => { c[j.id] = "titulaire"; });
    (bloc.banc || []).forEach((j) => { c[j.id] = "remplacant"; });
    setChoix(c);
    setFormation(bloc.formation || "");
    setStaffId(bloc.staff ? String(bloc.staff.id) : "");
  }, [compo, equipe]);

  const comptes = useMemo(() => {
    const vals = Object.values(choix);
    return {
      titulaires: vals.filter((v) => v === "titulaire").length,
      banc: vals.filter((v) => v === "remplacant").length,
    };
  }, [choix]);

  const maxBanc = compo?.max_remplacants ?? 7;

  async function enregistrer() {
    setMsg(""); setErreur("");
    const lignes = Object.entries(choix)
      .filter(([, v]) => v)
      .map(([id, v]) => ({ joueur_id: Number(id), statut: v }));
    try {
      const neuf = await api.enregistrerComposition(matchId, {
        equipe,
        formation: formation || null,
        staff_id: staffId ? Number(staffId) : null,
        joueurs: lignes,
      });
      setCompo(neuf);
      setMsg("Composition enregistrée.");
    } catch (e) {
      setErreur(e?.message || "Enregistrement refusé.");
    }
  }

  if (!moi || !match) return <p className="empty">Chargement…</p>;
  if (!equipe) return <p className="empty">Ce match ne concerne pas votre club.</p>;

  const nomClub = stripDemo(clubsById?.[clubId]?.nom) || "Votre club";
  return (
    <section className="hero">
      <p className="kicker">Feuille de composition</p>
      <h1>{nomClub}</h1>
      <p className="lead">Sélectionnez depuis votre effectif enregistré. Titulaires {comptes.titulaires}/11 · Banc {comptes.banc}/{maxBanc}.</p>
      <div className="editeur-reglages">
        <label className="editeur-champ">
          <span>Formation</span>
          <input value={formation} onChange={(e) => setFormation(e.target.value)} placeholder="4-3-3" maxLength={12} />
        </label>
        <span className="editeur-formations">
          {FORMATIONS.map((f) => (
            <button key={f} type="button" className="editeur-chip" onClick={() => setFormation(f)}>{f}</button>
          ))}
        </span>
        <label className="editeur-champ">
          <span>Entraîneur</span>
          <select value={staffId} onChange={(e) => setStaffId(e.target.value)}>
            <option value="">— À compléter —</option>
            {staff.map((s) => (
              <option key={s.id} value={s.id}>{s.nom_complet || s.full_name}{s.role ? ` · ${s.role}` : ""}</option>
            ))}
          </select>
        </label>
      </div>
      <div className="section-head"><h2>Effectif</h2></div>
      {joueurs.length === 0 && <p className="empty">Aucun joueur enregistré pour ce club.</p>}
      {joueurs.map((j) => (
        <div key={j.id} className="editeur-ligne">
          <span className="feuille-photo" aria-hidden="true">
            {j.photo_url ? <img src={j.photo_url} alt="" /> : (j.nom_complet || "?").charAt(0)}
          </span>
          <span className="editeur-id">
            <span className="feuille-nom">{j.nom_complet}</span>
            <span className="meta-line">{labelPoste(j.poste) || "Poste"}{j.numero ? ` · N° ${j.numero}` : ""}</span>
          </span>
          <span className="editeur-seg">
            {["titulaire", "remplacant"].map((v) => (
              <button
                key={v}
                type="button"
                className={`editeur-bouton${choix[j.id] === v ? " actif" : ""}`}
                onClick={() => setChoix((c) => ({ ...c, [j.id]: c[j.id] === v ? undefined : v }))}
              >
                {v === "titulaire" ? "Titulaire" : "Banc"}
              </button>
            ))}
          </span>
        </div>
      ))}
      {msg && <p className="editeur-msg">{msg}</p>}
      {erreur && <p className="editeur-erreur">{erreur}</p>}
      <button type="button" className="editeur-enregistrer" onClick={enregistrer}>Enregistrer la feuille</button>
    </section>
  );
}
