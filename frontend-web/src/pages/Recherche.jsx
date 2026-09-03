import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api.js";
import { clubName, useKivu } from "../context.jsx";
import { stripDemo } from "../display.js";

function norm(s) {
  return (s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

export default function Recherche() {
  const [params] = useSearchParams();
  const q = (params.get("q") || "").trim();
  const nq = norm(q);
  const { clubs, saison, clubsById } = useKivu();
  const [joueurs, setJoueurs] = useState([]);
  const [matchs, setMatchs] = useState([]);

  useEffect(() => {
    api.joueurs().then(setJoueurs).catch(() => setJoueurs([]));
  }, []);

  useEffect(() => {
    if (!saison) return;
    api.matchs(saison.id).then(setMatchs).catch(() => setMatchs([]));
  }, [saison]);

  const clubsTrouves = useMemo(
    () => (clubs || []).filter((c) => norm(stripDemo(c.nom)).includes(nq)),
    [clubs, nq],
  );
  const joueursTrouves = useMemo(
    () => (joueurs || []).filter((j) => norm(j.nom_complet).includes(nq)),
    [joueurs, nq],
  );
  const matchsTrouves = useMemo(
    () =>
      (matchs || []).filter((m) => {
        const a = norm(stripDemo(clubName(clubsById, m.equipe_domicile_id)));
        const b = norm(stripDemo(clubName(clubsById, m.equipe_exterieur_id)));
        return a.includes(nq) || b.includes(nq);
      }),
    [matchs, clubsById, nq],
  );

  const vide = !nq || (clubsTrouves.length + joueursTrouves.length + matchsTrouves.length === 0);

  return (
    <section className="hero">
      <p className="kicker">Recherche</p>
      <h1>{q || "Rechercher"}</h1>
      {!nq && <p className="empty">Saisir un club, un joueur ou un match.</p>}
      {nq && vide && <p className="empty">Aucun résultat pour « {q} ».</p>}

      {clubsTrouves.length > 0 && (
        <>
          <div className="section-head"><h2>Clubs</h2></div>
          <div className="sheet">
            {clubsTrouves.map((c) => (
              <Link key={c.id} to={`/clubs/${c.id}`} className="club-tile">
                <strong>{stripDemo(c.nom)}</strong>
                <span className="meta">{[c.ville, c.stade].filter(Boolean).join(" — ")}</span>
              </Link>
            ))}
          </div>
        </>
      )}

      {joueursTrouves.length > 0 && (
        <>
          <div className="section-head"><h2>Joueurs</h2></div>
          <div className="sheet">
            {joueursTrouves.map((j) => (
              <Link key={j.id} to={`/joueurs/${j.id}`} className="club-tile">
                <strong>{j.nom_complet}</strong>
                <span className="meta">{stripDemo(clubName(clubsById, j.club_actuel_id))}</span>
              </Link>
            ))}
          </div>
        </>
      )}

      {matchsTrouves.length > 0 && (
        <>
          <div className="section-head"><h2>Matchs</h2></div>
          <div className="sheet">
            {matchsTrouves.map((m) => (
              <Link key={m.id} to={`/matchs/${m.id}`} className="club-tile">
                <strong>
                  {stripDemo(clubName(clubsById, m.equipe_domicile_id))}
                  {" · "}
                  {stripDemo(clubName(clubsById, m.equipe_exterieur_id))}
                </strong>
                <span className="meta">{m.statut}</span>
              </Link>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
