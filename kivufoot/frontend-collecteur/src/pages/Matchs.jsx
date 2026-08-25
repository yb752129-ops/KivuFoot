import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchMatchsDisponibles } from "../lib/api";
import { db } from "../lib/db";
import IndicateurSync from "../components/IndicateurSync";

export default function Matchs() {
  const [matchs, setMatchs] = useState([]);
  const [horsLigne, setHorsLigne] = useState(!navigator.onLine);

  useEffect(() => {
    async function charger() {
      try {
        const distants = await fetchMatchsDisponibles();
        setMatchs(distants);
        await db.matchsCache.bulkPut(distants);
        setHorsLigne(false);
      } catch {
        // Pas de réseau : on retombe sur le cache local (§12.3).
        const locaux = await db.matchsCache.toArray();
        setMatchs(locaux);
        setHorsLigne(true);
      }
    }
    charger();
  }, []);

  return (
    <div className="page page-matchs">
      <header>
        <h1>Mes matchs</h1>
        <IndicateurSync />
      </header>
      {horsLigne && <p className="banniere-offline">Mode hors-ligne : liste mise en cache.</p>}
      <ul className="liste-matchs">
        {matchs.map((m) => (
          <li key={m.id}>
            <Link to={`/matchs/${m.id}/saisie`}>
              Match #{m.id} — {new Date(m.date_heure).toLocaleString("fr-FR")} — {m.statut}
            </Link>
          </li>
        ))}
        {matchs.length === 0 && <p>Aucun match disponible pour le moment.</p>}
      </ul>
    </div>
  );
}
