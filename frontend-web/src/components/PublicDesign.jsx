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

export const PUBLIC_SCORE_STATUSES = ["en_cours", "termine", "valide"];

export function scorePublicVisible(match) {
  return PUBLIC_SCORE_STATUSES.includes(match?.statut);
}

export function compareClassementRows(a, b) {
  const aActif = !a?.statut || a.statut === "actif";
  const bActif = !b?.statut || b.statut === "actif";
  if (aActif !== bActif) return aActif ? -1 : 1;
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

export const STATUT_EQUIPE_PUBLIC = {
  actif: null,
  disqualifie: { label: "Disqualifié", court: "DISQ." },
  elimine: { label: "Éliminé", court: "ÉLIM." },
};

export function statutEquipePublic(statut) {
  return STATUT_EQUIPE_PUBLIC[String(statut || "actif")] || null;
}

function IcoInterdit() {
  return (
    <svg className="kf-team-status-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <circle cx="12" cy="12" r="8.5" />
      <path d="m6 6 12 12" />
    </svg>
  );
}

export function StatutEquipeBadge({ statut, compact = false }) {
  const info = statutEquipePublic(statut);
  if (!info) return null;
  return (
    <span className={`kf-team-status-badge${compact ? " is-compact" : ""}`} title={info.label} aria-label={info.label}>
      <IcoInterdit />
      <span className="kf-team-status-label">{info.label}</span>
      <strong>{info.court}</strong>
    </span>
  );
}

export function findPublicClub(clubsById, saisonClubs, id) {
  const numericId = Number(id);
  const scoped = (saisonClubs || []).find((club) => Number(club.id ?? club.club_id) === numericId);
  const global = clubsById?.[id] || clubsById?.[numericId] || null;
  // La ligne d'inscription est prioritaire : c'est elle qui connaît le
  // statut propre à l'édition (les clubs globaux ne le connaissent pas).
  return scoped || global || null;
}

export function publicClubName(clubsById, saisonClubs, id) {
  const club = findPublicClub(clubsById, saisonClubs, id);
  return club?.nom ? stripDemo(club.nom) : "—";
}

export function PublicClubLogo({ club, name, className = "club-logo", statut = club?.statut }) {
  const grayscale = statut && statut !== "actif" ? " is-status-muted" : "";
  if (club?.logo_url) {
    return <img className={`${className}${grayscale}`} src={club.logo_url} alt={`Logo ${name || "—"}`} loading="lazy" />;
  }
  return <span className={`${className} club-logo-missing${grayscale}`} aria-label="Logo absent">—</span>;
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

export function formatPublicKickoff(iso) {
  if (!iso || !/[T ]\d{2}:\d{2}/.test(String(iso))) return "Heure à confirmer";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "Heure à confirmer";
  const jour = new Intl.DateTimeFormat("fr-FR", {
    weekday: "short",
    day: "numeric",
    month: "short",
    timeZone: TZ_SUD_KIVU,
  }).format(date);
  const heure = new Intl.DateTimeFormat("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: TZ_SUD_KIVU,
  }).format(date);
  return `${jour} · ${heure}`;
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
  if (!scorePublicVisible(match)) return "—";
  return `${displayValue(match?.score_domicile)}–${displayValue(match?.score_exterieur)}`;
}
