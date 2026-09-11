import { useEffect, useRef, useState } from "react";
import { api } from "../../api.js";
import { useKivu } from "../../context.jsx";
import { stripDemo } from "../../display.js";

const ROLES = [
  "ENTRAINEUR_PRINCIPAL",
  "ADJOINT",
  "ENTRAINEUR_GARDIENS",
  "PREPARATEUR_PHYSIQUE",
  "ANALYSTE",
  "TEAM_MANAGER",
  "MEDICAL",
  "AUTRE",
];

function roleLabel(r) {
  return String(r || "").replace(/_/g, " ").toLowerCase();
}

export default function Coach() {
  const { clubsById } = useKivu();
  const [moi, setMoi] = useState(null);
  const [staff, setStaff] = useState([]);
  const [msg, setMsg] = useState("");
  const [erreur, setErreur] = useState("");
  const [nom, setNom] = useState("");
  const [role, setRole] = useState(ROLES[0]);
  const [editId, setEditId] = useState(null);
  const [editNom, setEditNom] = useState("");
  const [editRole, setEditRole] = useState(ROLES[0]);
  const inputs = useRef({});

  useEffect(() => {
    api.me().then(setMoi).catch(() => setMoi(null));
  }, []);

  const clubId = moi?.club_id ?? null;

  useEffect(() => {
    if (!clubId) return;
    api.staffClub(clubId).then(setStaff).catch(() => setStaff([]));
  }, [clubId]);

  async function envoyer(staffId, fichier) {
    setMsg(""); setErreur("");
    try {
      await api.photoStaff(staffId, fichier);
      setMsg("Photo envoyée. L'organisateur la vérifie avant publication.");
      const frais = await api.staffClub(clubId);
      setStaff(frais);
    } catch (e) {
      setErreur(e?.message || "Envoi refusé.");
    }
  }

  async function ajouter() {
    setMsg(""); setErreur("");
    if (!nom.trim()) { setErreur("Donnez d'abord un nom."); return; }
    try {
      await api.creerStaff(clubId, { nom_complet: nom.trim(), role: String(role).toLowerCase() });
      setNom("");
      setMsg("Membre du staff ajouté. Vous pouvez maintenant proposer sa photo.");
      const frais = await api.staffClub(clubId);
      setStaff(frais);
    } catch (e) {
      setErreur(e?.message || "Ajout refusé.");
    }
  }

  async function modifier(staffId) {
    setMsg(""); setErreur("");
    if (!editNom.trim()) { setErreur("Donnez d'abord un nom."); return; }
    try {
      await api.modifierStaff(staffId, { nom_complet: editNom.trim(), role: String(editRole).toLowerCase() });
      setEditId(null);
      setMsg("Membre mis à jour.");
      const frais = await api.staffClub(clubId);
      setStaff(frais);
    } catch (e) {
      setErreur(e?.message || "Modification refusée.");
    }
  }

  async function retirer(staffId, nomMembre) {
    setMsg(""); setErreur("");
    if (!window.confirm("Retirer " + nomMembre + " du staff ?")) return;
    try {
      await api.retirerStaff(staffId);
      setMsg("Membre retiré du staff.");
      const frais = await api.staffClub(clubId);
      setStaff(frais);
    } catch (e) {
      setErreur(e?.message || "Retrait refusé.");
    }
  }

  if (!moi) return <p className="empty">Chargement…</p>;
  if (!clubId) return <p className="empty">Votre compte n'est rattaché à aucun club.</p>;

  return (
    <section className="hero">
      <p className="kicker">Espace coach et staff</p>
      <h1>{stripDemo(clubsById?.[clubId]?.nom) || "Votre club"}</h1>
      <p className="lead">La photo proposée reste invisible du public tant que l'organisateur ne l'a pas validée. L'ancienne photo validée reste affichée pendant la vérification.</p>

      <div className="section-head"><h2>Membres du staff</h2></div>
      {staff.length === 0 && <p className="empty">Aucun membre du staff pour le moment.</p>}
      {staff.map((m) => (
        <div key={m.id} className="coach-ligne">
          <span className="feuille-photo" aria-hidden="true">
            {m.photo_url ? <img src={m.photo_url} alt="" /> : (m.nom_complet || "?").charAt(0)}
          </span>
          <span className="coach-id">
            <span className="feuille-nom">{m.nom_complet}</span>
            <span className="meta-line">{roleLabel(m.role)}</span>
          </span>
          <span className="coach-etat">
            {m.photo_en_attente ? "Photo en vérification" : m.photo_url ? "Photo validée" : "Pas de photo"}
          </span>
          <button
            type="button"
            className="editeur-bouton"
            onClick={() => inputs.current[m.id]?.click()}
          >
            {m.photo_url ? "Remplacer la photo" : "Ajouter une photo"}
          </button>
          <input
            ref={(el) => { inputs.current[m.id] = el; }}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            style={{ display: "none" }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) envoyer(m.id, f);
              e.target.value = "";
            }}
          />
          <span className="coach-actions">
            <button
              type="button"
              className="editeur-bouton"
              onClick={() => {
                if (editId === m.id) { setEditId(null); return; }
                setEditId(m.id);
                setEditNom(m.nom_complet);
                setEditRole(String(m.role).toUpperCase());
              }}
            >
              {editId === m.id ? "Fermer" : "Modifier"}
            </button>
            <button type="button" className="editeur-bouton coach-retirer" onClick={() => retirer(m.id, m.nom_complet)}>
              Retirer
            </button>
            {editId === m.id && (
              <span className="coach-edit">
                <label className="editeur-champ">
                  <span>Nom complet</span>
                  <input value={editNom} onChange={(e) => setEditNom(e.target.value)} />
                </label>
                <label className="editeur-champ">
                  <span>Rôle</span>
                  <select value={editRole} onChange={(e) => setEditRole(e.target.value)}>
                    {ROLES.map((r) => <option key={r} value={r}>{roleLabel(r)}</option>)}
                  </select>
                </label>
                <button type="button" className="editeur-bouton" onClick={() => modifier(m.id)}>Enregistrer</button>
              </span>
            )}
          </span>
        </div>
      ))}

      <div className="section-head"><h2>Ajouter un membre</h2></div>
      <div className="editeur-reglages">
        <label className="editeur-champ">
          <span>Nom complet</span>
          <input value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom et prénom" />
        </label>
        <label className="editeur-champ">
          <span>Rôle</span>
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            {ROLES.map((r) => <option key={r} value={r}>{roleLabel(r)}</option>)}
          </select>
        </label>
        <button type="button" className="editeur-bouton" onClick={ajouter}>Ajouter</button>
      </div>

      {msg && <p className="editeur-msg">{msg}</p>}
      {erreur && <p className="editeur-erreur">{erreur}</p>}
    </section>
  );
}
