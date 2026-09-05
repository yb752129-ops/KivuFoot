import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "./api.js";

const Ctx = createContext(null);
const COMP_KEY = "kivufoot_competition_id";

export function useKivu() {
  return useContext(Ctx);
}

function lireId() {
  try {
    const n = Number(localStorage.getItem(COMP_KEY));
    return Number.isFinite(n) && n > 0 ? n : 0;
  } catch {
    return 0;
  }
}

function choisirDans(list) {
  if (!list?.length) return null;
  const saved = lireId();
  return list.find((c) => c.id === saved) || list.find((c) => !c.est_demo) || list[0];
}

export function KivuProvider({ children }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [competitions, setCompetitions] = useState([]);
  const [competition, setCompetition] = useState(null);
  const [saison, setSaison] = useState(null);
  const [clubs, setClubs] = useState([]);
  const [saisonClubs, setSaisonClubs] = useState(null);

  async function chargerClubsSaison(saisonId) {
    if (!saisonId) {
      setSaisonClubs([]);
      return [];
    }
    try {
      const sc = await api.clubsSaison(saisonId);
      setSaisonClubs(sc || []);
      return sc || [];
    } catch {
      setSaisonClubs(null);
      return null;
    }
  }

  async function chargerSaison(comp) {
    if (!comp) {
      setSaison(null);
      setSaisonClubs([]);
      return;
    }
    const saisons = await api.saisons(comp.id);
    const s = saisons?.[0] || null;
    setSaison(s);
    await chargerClubsSaison(s?.id);
  }

  async function rechargerClubs() {
    const clubList = (await api.clubs()) || [];
    setClubs(clubList);
    return clubList;
  }

  useEffect(() => {
    let stop = false;
    (async () => {
      try {
        const [comps, clubList] = await Promise.all([api.competitions(), api.clubs()]);
        if (stop) return;
        const list = comps || [];
        const comp = choisirDans(list);
        setCompetitions(list);
        setCompetition(comp);
        setClubs(clubList || []);
        if (comp) {
          const saisons = await api.saisons(comp.id);
          const s = saisons?.[0] || null;
          if (!stop) {
            setSaison(s);
            if (s) {
              try {
                const sc = await api.clubsSaison(s.id);
                if (!stop) setSaisonClubs(sc || []);
              } catch {
                if (!stop) setSaisonClubs(null);
              }
            } else if (!stop) {
              setSaisonClubs([]);
            }
          }
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

  async function choisirCompetition(id, list = competitions) {
    const comp = list.find((c) => c.id === Number(id)) || null;
    setCompetition(comp);
    try {
      if (comp) localStorage.setItem(COMP_KEY, String(comp.id));
    } catch {
      /* ignore */
    }
    try {
      await chargerSaison(comp);
    } catch (e) {
      setError(e.message || "Saison indisponible");
    }
  }

  async function rechargerCompetitions() {
    const list = (await api.competitions()) || [];
    setCompetitions(list);
    return list;
  }

  const clubsById = useMemo(() => Object.fromEntries(clubs.map((c) => [c.id, c])), [clubs]);

  return (
    <Ctx.Provider
      value={{
        loading,
        error,
        competitions,
        competition,
        saison,
        clubs,
        saisonClubs,
        clubsById,
        choisirCompetition,
        rechargerCompetitions,
        rechargerClubs,
        chargerClubsSaison,
        setClubs,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function clubName(clubsById, id) {
  return clubsById[id]?.nom || `Club #${id}`;
}
