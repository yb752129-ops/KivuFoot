import { useEffect, useMemo, useRef, useState } from "react";
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

function RankingRow({ ligne, index, club, details, followedClubId }) {
  const nom = nomClub(ligne, club);
  const followed = followedClubId !== null && Number(ligne.club_id) === followedClubId;
  const contenu = (
    <>
      <PublicClubLogo club={club} name={nom} />
      <span className="kf-public-rank-name">{nom}</span>
    </>
  );
  return (
    <tr className={followed ? "followed" : ""}>
      <td className="kf-public-rank-position">{index + 1}</td>
      <td className="kf-public-rank-club">
        {ligne.club_id ? <Link to={`/clubs/${ligne.club_id}`}>{contenu}</Link> : <span>{contenu}</span>}
      </td>
      <td><strong>{displayValue(ligne.points)}</strong></td>
      <td>{displayValue(ligne.matchs_joues)}</td>
      <td>{displayDifference(ligne.difference_buts)}</td>
      {details && (
        <>
          <td>{displayValue(ligne.victoires)}</td>
          <td>{displayValue(ligne.nuls)}</td>
          <td>{displayValue(ligne.defaites)}</td>
          <td>{displayValue(ligne.buts_marques)}</td>
          <td>{displayValue(ligne.buts_encaisses)}</td>
        </>
      )}
    </tr>
  );
}

export default function Classement() {
  const { saison, saisonClubs, clubsById } = useKivu();
  const [lignes, setLignes] = useState([]);
  const [groupes, setGroupes] = useState([]);
  const [groupe, setGroupe] = useState("");
  const [details, setDetails] = useState(false);
  const [detailsAtEnd, setDetailsAtEnd] = useState(false);
  const detailsTableScrollRef = useRef(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    const configured = new Set(
      (saisonClubs || [])
        .map((club) => String(club.groupe || "").toUpperCase())
        .filter(Boolean),
    );
    const available = GROUPES.filter((item) => configured.has(item));
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

  useEffect(() => {
    setDetailsAtEnd(false);
    if (!details) return undefined;
    const element = detailsTableScrollRef.current;
    if (!element) return undefined;
    const updateScrollHint = () => {
      setDetailsAtEnd(element.scrollLeft + element.clientWidth >= element.scrollWidth - 2);
    };
    updateScrollHint();
    element.addEventListener("scroll", updateScrollHint, { passive: true });
    window.addEventListener("resize", updateScrollHint);
    return () => {
      element.removeEventListener("scroll", updateScrollHint);
      window.removeEventListener("resize", updateScrollHint);
    };
  }, [details, lignesTriees.length]);
  const followedClubId = followedPublicClubId();
  const clubSuivi = followedClubId === null
    ? null
    : lignesTriees.find((ligne) => Number(ligne.club_id) === followedClubId);
  const equipesSuivies = Boolean(clubSuivi);
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
        {groupes.map((item) => (
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

      <div className="kf-public-ranking-tools">
        {equipesSuivies ? <span className="kf-public-followed-note">{nomClub(clubSuivi, findPublicClub(clubsById, saisonClubs, clubSuivi.club_id))} · équipe suivie</span> : <span />}
        <button
          type="button"
          className="kf-public-outline-button"
          aria-expanded={details}
          onClick={() => setDetails((value) => !value)}
        >
          {details ? "Masquer les détails" : "Détails"} <span aria-hidden="true">⌄</span>
        </button>
      </div>

      {lignesTriees.length === 0 ? (
        <div className="kf-public-empty"><strong>Aucune donnée disponible</strong></div>
      ) : (
        <div
          ref={detailsTableScrollRef}
          className={`kf-public-table-scroll${details ? " kf-public-table-scroll-details" : ""}${details && detailsAtEnd ? " is-at-end" : ""}`}
        >
          <table className={`kf-public-rank-table${details ? " details" : ""}`}>
            <thead>
              <tr>
                <th>#</th><th>Club</th><th>Pts</th><th>J</th><th>Diff</th>
                {details && <><th>G</th><th>N</th><th>P</th><th>BP</th><th>BC</th></>}
              </tr>
            </thead>
            <tbody>
              {lignesTriees.map((ligne, index) => (
                <RankingRow
                  key={`${ligne.club_id ?? "missing"}-${index}`}
                  ligne={ligne}
                  index={index}
                  club={findPublicClub(clubsById, saisonClubs, ligne.club_id)}
                  details={details}
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
