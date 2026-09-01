import { createContext, useContext, useEffect, useState } from "react";
import { api, clearTokens, getToken, setTokens } from "./api.js";

const ME_KEY = "kivufoot_me";
const REFRESH_KEY = "kivufoot_refresh";
const Ctx = createContext(null);

export function useAuth() {
  return useContext(Ctx);
}

function lireMe() {
  try {
    return JSON.parse(localStorage.getItem(ME_KEY) || "null");
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(lireMe);

  useEffect(() => {
    if (!getToken()) return;
    api.me()
      .then((me) => {
        localStorage.setItem(ME_KEY, JSON.stringify(me));
        setUser(me);
      })
      .catch(() => {
        clearTokens();
        localStorage.removeItem(ME_KEY);
        setUser(null);
      });
  }, []);

  async function applySession(tokens) {
    setTokens(tokens.access_token, tokens.refresh_token);
    const me = await api.me();
    localStorage.setItem(ME_KEY, JSON.stringify(me));
    setUser(me);
    return me;
  }

  async function logout() {
    const refresh = localStorage.getItem(REFRESH_KEY);
    if (refresh) {
      try {
        await api.logout(refresh);
      } catch {
        /* session locale quand même coupée */
      }
    }
    clearTokens();
    localStorage.removeItem(ME_KEY);
    setUser(null);
  }

  const prenom = (user?.nom_complet || "").trim().split(/\s+/)[0] || "";

  return (
    <Ctx.Provider value={{ user, prenom, applySession, logout }}>
      {children}
    </Ctx.Provider>
  );
}
