import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "./api.js";

const Ctx = createContext(null);

export function useKivu() {
  return useContext(Ctx);
}

export function KivuProvider({ children }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [competition, setCompetition] = useState(null);
  const [saison, setSaison] = useState(null);
  const [clubs, setClubs] = useState([]);

  useEffect(() => {
    let stop = false;
    (async () => {
      try {
        const [comps, clubList] = await Promise.all([api.competitions(), api.clubs()]);
        if (stop) return;
        const comp = comps?.[0] || null;
        setCompetition(comp);
        setClubs(clubList || []);
        if (comp) {
          const saisons = await api.saisons(comp.id);
          if (!stop) setSaison(saisons?.[0] || null);
        }
      } catch (e) {
        if (!stop) setError(e.message || "API indisponible");
      } finally {
        if (!stop) setLoading(false);
      }
    })();
    return () => {
      stop = true;
    };
  }, []);

  const clubsById = useMemo(() => Object.fromEntries(clubs.map((c) => [c.id, c])), [clubs]);

  return (
    <Ctx.Provider value={{ loading, error, competition, saison, clubs, clubsById }}>
      {children}
    </Ctx.Provider>
  );
}

export function clubName(clubsById, id) {
  return clubsById[id]?.nom || `Club #${id}`;
}
