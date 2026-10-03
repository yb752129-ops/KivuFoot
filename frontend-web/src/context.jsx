import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "./api.js";

const Ctx = createContext(null);
const COMP_KEY = "kivufoot_competition_id";
const SEASON_KEY = "kivufoot_saison_id";

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

function lireSaisonId() {
  try {
    const n = Number(localStorage.getItem(SEASON_KEY));
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
  const [saisons, setSaisons] = useState([]);
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

  async function chargerSaison(comp, saisonId = 0) {
    if (!comp) {
      setSaisons([]);
      setSaison(null);
      setSaisonClubs([]);
      return;
    }
    const rows = (await api.saisons(comp.id)) || [];
    setSaisons(rows);
    const saved = saisonId || lireSaisonId();
    const s = rows.find((row) => row.id === saved)
      || rows.find((row) => !row.date_fin)
      || rows[0]
      || null;
    setSaison(s);
    if (s) {
      try { localStorage.setItem(SEASON_KEY, String(s.id)); } catch { /* ignore */ }
    }
    await chargerClubsSaison(s?.id);
  }

  async function rechargerClubs() {
    const clubList = (await api.clubs()) || [];
    setClubs(clubList);
    return clubList;
  }

  async function chargerTout() {
    setError("");
    setLoading(true);
    try {
      const [comps, clubList] = await Promise.all([api.competitions(), api.clubs()]);
      const list = comps || [];
      const comp = choisirDans(list);
      setCompetitions(list);
      setCompetition(comp);
      setClubs(clubList || []);
      if (comp) {
        await chargerSaison(comp);
      } else {
        setSaisons([]);
        setSaison(null);
        setSaisonClubs([]);
      }
    } catch (e) {
      setError(e.message || "API indisponible");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    chargerTout();
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

  async function choisirSaison(id) {
    const next = saisons.find((row) => row.id === Number(id)) || null;
    setSaison(next);
    try {
      if (next) localStorage.setItem(SEASON_KEY, String(next.id));
    } catch { /* ignore */ }
    await chargerClubsSaison(next?.id);
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
        saisons,
        saison,
        choisirSaison,
        clubs,
        saisonClubs,
        clubsById,
        choisirCompetition,
        rechargerCompetitions,
        rechargerClubs,
        chargerClubsSaison,
        reessayer: chargerTout,
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
