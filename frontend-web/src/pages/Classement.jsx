import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";
import { stripDemo } from "../display.js";

const GROUPES = ["A", "B", "C", "D"];

function LogoClub({ club, nom }) {
  if (club?.logo_url) {
    return <img className="classement-logo" src={club.logo_url} alt={`Logo ${stripDemo(nom)}`} loading="lazy" />;
  }
  return <span className="classement-logo classement-logo-vide" aria-hidden="true">{stripDemo(nom || "?").slice(0, 2).toUpperCase()}</span>;
}

export default function Classement() {
  const { saison, saisonClubs, clubsById } = useKivu();
  const [lignes, setLignes] = useState([]);
  const [groupes, setGroupes] = useState([]);
  const [groupe, setGroupe] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    const configured = new Set((saisonClubs || []).map((club) => club.groupe).filter(Boolean));
    const available = GROUPES.filter((g) => configured.has(g));
    setGroupes(available);
    if (groupe && !available.includes(groupe)) setGroupe("");
  }, [saisonClubs, groupe]);

  useEffect(() => {
    if (!saison) {
      setLignes([]);
      return undefined;
    }
    let stop = false;
    setErr("");
    api.classement(saison.id, groupe || undefined)
      .then((l) => { if (!stop) setLignes(l || []); })
      .catch((e) => { if (!stop) setErr(e.message); });
    return () => { stop = true; };
  }, [saison, groupe, saisonClubs]);

  return (
    <section className="hero">
      <div className="section-head" style={{ marginTop: 0 }}>
        <h1 style={{ margin: 0 }}>Classement</h1>
        <Link to="/buteurs">Buteurs</Link>
      </div>
      {groupes.length > 0 && (
        <div className="pills" role="tablist" aria-label="Filtrer par groupe">
          <button type="button" className={`pill${groupe === "" ? " pill-active" : ""}`} onClick={() => setGroupe("")}>
            Général
          </button>
          {groupes.map((g) => (
            <button key={g} type="button" className={`pill${groupe === g ? " pill-active" : ""}`} onClick={() => setGroupe(g)}>
              Groupe {g}
            </button>
          ))}
        </div>
      )}
      {err && <p className="erreur">{err}</p>}
      <div className="table-wrap">
        {lignes.length === 0 && <p className="empty">Aucune équipe ou aucun résultat pour ce filtre.</p>}
        {lignes.length > 0 && (
          <table className="table table-accueil">
            <thead>
              <tr>
                <th>#</th><th>Club</th><th>Pts</th><th>J</th><th>G</th><th>N</th><th>P</th><th>BP</th><th>BC</th><th>Diff</th>
              </tr>
            </thead>
            <tbody>
              {lignes.map((l, i) => {
                const club = clubsById[l.club_id] || (saisonClubs || []).find((item) => item.id === l.club_id || item.club_id === l.club_id);
                return (
                  <tr key={l.club_id}>
                    <td className="pos">{i + 1}</td>
                    <td>
                      <Link to={`/clubs/${l.club_id}`} className="classement-club-cell">
                        <LogoClub club={club} nom={l.club_nom} />
                        <span>{stripDemo(l.club_nom)}</span>
                      </Link>
                    </td>
                    <td><strong>{l.points}</strong></td>
                    <td>{l.matchs_joues}</td>
                    <td>{l.victoires}</td>
                    <td>{l.nuls}</td>
                    <td>{l.defaites}</td>
                    <td>{l.buts_marques}</td>
                    <td>{l.buts_encaisses}</td>
                    <td>{l.difference_buts > 0 ? `+${l.difference_buts}` : l.difference_buts}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
