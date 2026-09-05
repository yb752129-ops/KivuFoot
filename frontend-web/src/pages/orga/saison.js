export async function assurerSaison({
  saison,
  competition,
  api,
  rechargerCompetitions,
  choisirCompetition,
  chargerClubsSaison,
}) {
  if (saison) return saison;
  if (!competition) throw new Error("Choisissez d’abord une compétition.");
  const existing = await api.saisons(competition.id);
  if (existing?.[0]) {
    await chargerClubsSaison(existing[0].id);
    return existing[0];
  }
  const created = await api.creerSaison({
    competition_id: competition.id,
    nom: competition.saison_label || null,
    club_ids: [],
  });
  const list = await rechargerCompetitions();
  await choisirCompetition(competition.id, list || []);
  return created;
}

export function isoDepuisDateHeure(date, heure) {
  if (!date || !heure) throw new Error("Indiquez la date et l’heure du match.");
  const d = new Date(`${date}T${heure}`);
  if (Number.isNaN(d.getTime())) throw new Error("Date ou heure invalide.");
  return d.toISOString();
}

export function fmtQuand(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

export const STATUT_MATCH = {
  programme: "Programmé",
  en_cours: "En cours",
  termine: "Terminé",
  valide: "Validé",
  conteste: "Contesté",
};
