export function stripDemo(name) {
  return (name || "").replace(/^DEMO\s*[-–]?\s*/i, "").trim();
}

/** Feuille : 1er jaune + rouge (2e jaune). Les jaunes extra restent en base. */
export function feuilleAffichee(evts) {
  const list = [...(evts || [])].sort(
    (a, b) =>
      (a.minute || 0) - (b.minute || 0)
      || (a.minute_additionnelle || 0) - (b.minute_additionnelle || 0)
      || (a.id || 0) - (b.id || 0),
  );
  const expulses2j = new Set(
    list
      .filter((e) => e.type === "carton_rouge" && e.source === "deuxieme_jaune" && !e.refuse)
      .map((e) => e.joueur_id),
  );
  const vuJaune = new Set();
  return list.filter((e) => {
    if (e.type !== "carton_jaune" || e.refuse || !expulses2j.has(e.joueur_id)) return true;
    if (vuJaune.has(e.joueur_id)) return false;
    vuJaune.add(e.joueur_id);
    return true;
  });
}

/** Bandeau live : plus récente minute, rouge avant jaune à minute égale. */
export function dernierFaitLive(evts) {
  const poids = (e) => {
    if (e.type === "carton_rouge") return 4;
    if (e.type === "but" || e.type === "but_contre_son_camp") return 3;
    if (e.type === "carton_jaune") return 2;
    return 1;
  };
  const list = feuilleAffichee(evts).filter((x) => !x.refuse);
  list.sort((a, b) => {
    const dm = (b.minute || 0) - (a.minute || 0);
    if (dm) return dm;
    const da = (b.minute_additionnelle || 0) - (a.minute_additionnelle || 0);
    if (da) return da;
    const dp = poids(b) - poids(a);
    if (dp) return dp;
    return (b.id || 0) - (a.id || 0);
  });
  return list[0] || null;
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

/** Jour civil Sud-Kivu (UTC+2, pas d’heure d’été). */
export const TZ_SUD_KIVU = "Africa/Lubumbashi";

export function civilDate(iso, timeZone = TZ_SUD_KIVU) {
  if (!iso) return "";
  const d = iso instanceof Date ? iso : new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(d);
  const get = (t) => parts.find((p) => p.type === t)?.value || "";
  return `${get("year")}-${get("month")}-${get("day")}`;
}

export function todayCivil(now = new Date(), timeZone = TZ_SUD_KIVU) {
  return civilDate(now, timeZone);
}

export function addCivilDays(yyyyMmDd, days) {
  const [y, m, d] = String(yyyyMmDd || "").split("-").map(Number);
  if (!y || !m || !d) return "";
  const dt = new Date(Date.UTC(y, m - 1, d + Number(days || 0)));
  const mm = String(dt.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(dt.getUTCDate()).padStart(2, "0");
  return `${dt.getUTCFullYear()}-${mm}-${dd}`;
}

export function formatHeure(iso, timeZone = TZ_SUD_KIVU) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone,
  });
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
