export function stripDemo(name) {
  return (name || "").replace(/^DEMO\s*[-–]?\s*/i, "").trim();
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
