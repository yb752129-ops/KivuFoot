export function stripDemo(name) {
  return (name || "").replace(/^DEMO\s*[-–]?\s*/i, "").trim();
}

export function labelEvenement(e) {
  if (e?.type === "carton_rouge" && e.source === "deuxieme_jaune") return "Rouge (2e jaune)";
  const labels = {
    but: "But",
    but_contre_son_camp: "CSC",
    passe_decisive: "Passe",
    carton_jaune: "Jaune",
    carton_rouge: "Rouge",
    remplacement: "Changement",
    penalty: "Penalty",
  };
  return labels[e?.type] || e?.type || "";
}

export const MOTIF_REFUS = {
  hors_jeu: "Hors-jeu",
  faute_attaquant: "Faute de l'attaquant",
  main: "Main",
  ballon_sorti: "Ballon sorti",
  faute_gardien: "Faute sur le gardien",
  autre: "Autre",
};

export function formatMinute(minute, added) {
  const m = Number(minute) || 0;
  const a = Number(added) || 0;
  if (a > 0) return `${m}+${a}′`;
  return `${m}′`;
}

export function periodeLabel(periode) {
  if (periode === "mi_temps") return "Mi-temps";
  if (periode === "2") return "2e période";
  if (periode === "1") return "1re période";
  return "";
}

export function elapsed(startedAt, endedAt, now = Date.now()) {
  if (!startedAt) return { min: 0, sec: 0 };
  const start = new Date(startedAt).getTime();
  const end = endedAt ? new Date(endedAt).getTime() : now;
  const ms = Math.max(0, end - start);
  return { min: Math.floor(ms / 60000), sec: Math.floor((ms % 60000) / 1000) };
}

/** Horloge de match : P1 depuis le coup d'envoi, P2 depuis la reprise (affiche 45+). */
export function clockFromMatch(match, now = Date.now()) {
  const periode = match?.periode || "1";
  if (!match?.started_at) return { min: 0, sec: 0, periode };
  if (periode === "mi_temps") {
    return { ...elapsed(match.started_at, match.paused_at || now, now), periode };
  }
  if (periode === "2" && match.periode_started_at) {
    const p2 = elapsed(match.periode_started_at, match.ended_at, now);
    return { min: 45 + p2.min, sec: p2.sec, periode };
  }
  return { ...elapsed(match.started_at, match.ended_at, now), periode };
}

export function formatClock(min, sec, periode) {
  const s = String(sec).padStart(2, "0");
  if (periode === "2") {
    if (min > 90) return `90+${min - 90}′${s}″`;
    return `${min}′${s}″`;
  }
  if (min > 45) return `45+${min - 45}′${s}″`;
  return `${min}′${s}″`;
}

export function splitMinute(min, periode) {
  const p = periode === "2" ? "2" : "1";
  const n = Math.max(0, Number.parseInt(String(min), 10) || 0);
  if (p === "1") {
    if (n > 45) return { minute: 45, minute_additionnelle: n - 45, periode: "1" };
    return { minute: n, minute_additionnelle: 0, periode: "1" };
  }
  if (n > 90) return { minute: 90, minute_additionnelle: n - 90, periode: "2" };
  return { minute: n, minute_additionnelle: 0, periode: "2" };
}

export function journeeTitre(code) {
  const m = String(code || "").match(/(\d+)/);
  return m ? `Journée ${m[1]}` : code || "Journée";
}

export function formatJour(iso, long = false) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(
    "fr-FR",
    long
      ? { day: "numeric", month: "long", year: "numeric" }
      : { day: "numeric", month: "short" }
  );
}

/** dim. 23 août — Stade Kadutu */
export function formatDateline(iso, stade) {
  const jour = iso
    ? new Date(iso).toLocaleDateString("fr-FR", {
        weekday: "short",
        day: "numeric",
        month: "short",
      })
    : "";
  return [jour, stade].filter(Boolean).join(" — ");
}

/** Groupes du plus récent au plus ancien. Même API, affichage seulement. */
export function groupMatchsByJournee(matchs) {
  const map = new Map();
  for (const m of matchs) {
    const key = m.journee || "—";
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(m);
  }
  const groups = [...map.entries()].map(([code, items]) => {
    const sorted = [...items].sort((a, b) => a.id - b.id);
    const latest = [...items].sort(
      (a, b) => new Date(b.date_heure) - new Date(a.date_heure)
    )[0];
    return { code, items: sorted, date: latest?.date_heure };
  });
  groups.sort((a, b) => new Date(b.date || 0) - new Date(a.date || 0));
  return groups;
}
