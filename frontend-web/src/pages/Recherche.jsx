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
          <div className="section-head"><h2>Équipes</h2></div>
          {clubsTrouves.map((c) => (
            <Link key={c.id} to={`/clubs/${c.id}`} className="avenir-row">
              <span className="avenir-noms">
                <span>{stripDemo(c.nom)}</span>
                <span className="meta-line">{[c.ville, c.stade].filter(Boolean).join(" — ")}</span>
              </span>
            </Link>
          ))}
        </>
      )}

      {joueursTrouves.length > 0 && (
        <>
          <div className="section-head"><h2>Joueurs</h2></div>
          {joueursTrouves.map((j) => (
            <Link key={j.id} to={`/joueurs/${j.id}`} className="avenir-row">
              <span className="avenir-noms">
                <span>{j.nom_complet}</span>
                <span className="meta-line">{stripDemo(clubName(clubsById, j.club_actuel_id))}</span>
              </span>
            </Link>
          ))}
        </>
      )}

      {matchsTrouves.length > 0 && (
        <>
          <div className="section-head"><h2>Matchs</h2></div>
          {matchsTrouves.map((m) => (
            <Link key={m.id} to={`/matchs/${m.id}`} className="avenir-row">
              <span className="avenir-noms">
                <span>
                  {stripDemo(clubName(clubsById, m.equipe_domicile_id))}
                  {" · "}
                  {stripDemo(clubName(clubsById, m.equipe_exterieur_id))}
                </span>
              </span>
            </Link>
          ))}
        </>
      )}
    </section>
  );
}
