import { stripDemo, TZ_SUD_KIVU, journeeTitre } from "../display.js";

export function displayValue(value) {
  return value === null || value === undefined || value === "" ? "—" : String(value);
}

export function displayDifference(value) {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  return number > 0 ? `+${number}` : String(number);
}

export function numericValue(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(String(value).replace("+", ""));
  return Number.isFinite(number) ? number : null;
}

export function compareClassementRows(a, b) {
  for (const [leftKey, rightKey] of [
    ["points", "points"],
    ["difference_buts", "difference_buts"],
    ["buts_marques", "buts_marques"],
  ]) {
    const left = numericValue(a?.[leftKey]);
    const right = numericValue(b?.[rightKey]);
    if (left === null && right === null) continue;
    if (left === null) return 1;
    if (right === null) return -1;
    if (left !== right) return right - left;
  }
  return 0;
}

export function followedPublicClubId() {
  if (typeof window === "undefined") return null;
  try {
    const id = Number(window.localStorage.getItem("kivufoot_club_suivi"));
    return Number.isInteger(id) && id > 0 ? id : null;
  } catch {
    return null;
  }
}

export function findPublicClub(clubsById, saisonClubs, id) {
  const numericId = Number(id);
  return clubsById?.[id]
    || clubsById?.[numericId]
    || (saisonClubs || []).find((club) => Number(club.id ?? club.club_id) === numericId)
    || null;
}

export function publicClubName(clubsById, saisonClubs, id) {
  const club = findPublicClub(clubsById, saisonClubs, id);
  return club?.nom ? stripDemo(club.nom) : "—";
}

export function PublicClubLogo({ club, name, className = "club-logo" }) {
  if (club?.logo_url) {
    return <img className={className} src={club.logo_url} alt={`Logo ${name || "—"}`} loading="lazy" />;
  }
  return <span className={`${className} club-logo-missing`} aria-label="Logo absent">—</span>;
}

export function formatPublicDate(iso) {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("fr-FR", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: TZ_SUD_KIVU,
  }).format(date);
}

export function formatPublicDay(iso) {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("fr-FR", {
    day: "numeric",
    month: "short",
    timeZone: TZ_SUD_KIVU,
  }).format(date);
}

export function formatPublicRound(value) {
  return value ? journeeTitre(value) : "—";
}

export function formatPublicScore(match) {
  if (match?.statut === "programme") return "—";
  return `${displayValue(match?.score_domicile)}–${displayValue(match?.score_exterieur)}`;
}
