import { createContext, useContext, useEffect, useState } from "react";

export const THEME_KEY = "kivufoot_apparence";

const Ctx = createContext(null);

export function resolveTheme(choice) {
  if (choice === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return choice === "dark" ? "dark" : "light";
}

export function applyTheme(choice) {
  const resolved = resolveTheme(choice);
  const root = document.documentElement;
  root.setAttribute("data-theme", resolved);
  root.style.colorScheme = resolved;
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", resolved === "dark" ? "#14120E" : "#F3EFE4");
}

export function ThemeProvider({ children }) {
  const [choice, setChoice] = useState(() => {
    try {
      return localStorage.getItem(THEME_KEY) || "light";
    } catch {
      return "light";
    }
  });

  useEffect(() => {
    applyTheme(choice);
    try {
      localStorage.setItem(THEME_KEY, choice);
    } catch {
      /* ignore */
    }
    if (choice !== "system") return undefined;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => applyTheme("system");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [choice]);

  return (
    <Ctx.Provider value={{ choice, setChoice, resolved: resolveTheme(choice) }}>
      {children}
    </Ctx.Provider>
  );
}

export function useTheme() {
  return useContext(Ctx);
}
