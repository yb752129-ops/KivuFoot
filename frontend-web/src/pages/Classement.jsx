import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useKivu } from "../context.jsx";
import { stripDemo } from "../display.js";
import {
  compareClassementRows,
  displayDifference,
  displayValue,
  findPublicClub,
  followedPublicClubId,
  PublicClubLogo,
} from "../components/PublicDesign.jsx";

const GROUPES = ["A", "B", "C", "D"];

function nomClub(ligne, club) {
  return stripDemo(ligne.club_nom || club?.nom || "—");
}

function RankingRow({ ligne, index, club, followedClubId }) {
  const nom = nomClub(ligne, club);
  const followed = followedClubId !== null && Number(ligne.club_id) === followedClubId;
  const contenu = (
    <span className="kf-public-rank-club-content">
      <span className="kf-public-rank-position">{index + 1}</span>
      <PublicClubLogo club={club} name={nom} />
      <span className="kf-public-rank-name">{nom}</span>
    </span>
  );
  return (
    <tr className={followed ? "followed" : ""}>
      <td className="kf-public-rank-club">
        {ligne.club_id ? <Link to={`/clubs/${ligne.club_id}`}>{contenu}</Link> : <span>{contenu}</span>}
      </td>
      <td><strong>{displayValue(ligne.points)}</strong></td>
      <td>{displayValue(ligne.matchs_joues)}</td>
      <td>{displayDifference(ligne.difference_buts)}</td>
      <td>{displayValue(ligne.victoires)}</td>
      <td>{displayValue(ligne.nuls)}</td>
      <td>{displayValue(ligne.defaites)}</td>
      <td>{displayValue(ligne.buts_marques)}</td>
      <td>{displayValue(ligne.buts_encaisses)}</td>
    </tr>
  );
}

export default function Classement() {
  const { saison, saisonClubs, clubsById } = useKivu();
  const [lignes, setLignes] = useState([]);
  const [groupe, setGroupe] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!saison) {
      setLignes([]);
      return undefined;
    }
    let stop = false;
    setErr("");
    api.classement(saison.id, groupe || undefined)
      .then((rows) => {
        if (!stop) setLignes(Array.isArray(rows) ? rows : []);
      })
      .catch((error) => {
        if (!stop) {
          setLignes([]);
          setErr(error.message || "Impossible de charger le classement.");
        }
      });
    return () => { stop = true; };
  }, [saison, groupe]);

  const lignesTriees = useMemo(() => [...lignes].sort(compareClassementRows), [lignes]);
  const followedClubId = followedPublicClubId();
  const clubSuivi = followedClubId === null
    ? null
    : lignesTriees.find((ligne) => Number(ligne.club_id) === followedClubId);
  const titreGroupe = groupe ? `Classement du groupe ${groupe}` : "Classement général";

  return (
    <section className="kf-public-page kf-public-ranking">
      <div className="kf-public-title-row">
        <div>
          <h1 className="screen-title">Classement</h1>
          <p className="screen-subtitle">{saison?.nom || "—"}</p>
        </div>
        <Link className="kf-public-text-link" to="/buteurs">Buteurs <span aria-hidden="true">→</span></Link>
      </div>

      <div className="kf-public-tabs" role="tablist" aria-label="Filtrer par groupe">
        <button
          type="button"
          role="tab"
          aria-selected={groupe === ""}
          className={groupe === "" ? "active" : ""}
          onClick={() => setGroupe("")}
        >
          Général
        </button>
        {GROUPES.map((item) => (
          <button
            key={item}
            type="button"
            role="tab"
            aria-selected={groupe === item}
            className={groupe === item ? "active" : ""}
            onClick={() => setGroupe(item)}
          >
            Groupe {item}
          </button>
        ))}
      </div>

      {err && <p className="kf-public-error">{err}</p>}

      <div className="kf-public-group-label">
        <strong>{titreGroupe}</strong>
        <span>{lignesTriees.length} équipes</span>
      </div>

      {clubSuivi && (
        <p className="kf-public-followed-note">
          {nomClub(clubSuivi, findPublicClub(clubsById, saisonClubs, clubSuivi.club_id))} · équipe suivie
        </p>
      )}

      {lignesTriees.length === 0 ? (
        <div className="kf-public-empty"><strong>Aucune donnée disponible</strong></div>
      ) : (
        <div className="kf-public-table-scroll">
          <table className="kf-public-rank-table">
            <thead>
              <tr>
                <th>Club</th>
                <th>Pts</th>
                <th>J</th>
                <th>Diff</th>
                <th>G</th>
                <th>N</th>
                <th>P</th>
                <th>BP</th>
                <th>BC</th>
              </tr>
            </thead>
            <tbody>
              {lignesTriees.map((ligne, index) => (
                <RankingRow
                  key={`${ligne.club_id ?? "missing"}-${index}`}
                  ligne={ligne}
                  index={index}
                  club={findPublicClub(clubsById, saisonClubs, ligne.club_id)}
                  followedClubId={followedClubId}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
