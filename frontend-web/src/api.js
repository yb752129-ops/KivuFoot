const API = (import.meta.env.VITE_API_BASE_URL || "https://kivufoot.onrender.com/api/v1").replace(/\/$/, "");

const TOKEN_KEY = "kivufoot_access";
const REFRESH_KEY = "kivufoot_refresh";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setTokens(access, refresh) {
  if (access) localStorage.setItem(TOKEN_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export function isAuthenticated() {
  return Boolean(getToken());
}

async function request(path, { method = "GET", body, auth = false } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const t = getToken();
    if (t) headers.Authorization = `Bearer ${t}`;
  }
  const res = await fetch(`${API}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return null;
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }
  if (!res.ok) {
    const detail = data?.detail;
    const msg = Array.isArray(detail)
      ? detail.map((d) => d.msg || JSON.stringify(d)).join(" ")
      : typeof detail === "string"
        ? detail
        : `Erreur ${res.status}`;
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  return data;
}

export const api = {
  competitions: () => request("/competitions?inclure_demo=true"),
  creerCompetition: (payload) => request("/competitions", { method: "POST", body: payload, auth: true }),
  saisons: (competitionId) => request(`/saisons?competition_id=${competitionId}`),
  creerSaison: (payload) => request("/saisons", { method: "POST", body: payload, auth: true }),
  clubs: () => request("/clubs?limit=100"),
  club: (id) => request(`/clubs/${id}`),
  creerClub: (payload) => request("/clubs", { method: "POST", body: payload, auth: true }),
  modifierClub: (id, payload) => request(`/clubs/${id}`, { method: "PUT", body: payload, auth: true }),
  supprimerClub: (id) => request(`/clubs/${id}`, { method: "DELETE", auth: true }),
  clubsSaison: (saisonId) => request(`/saisons/${saisonId}/clubs`),
  inscrireClub: (saisonId, clubId) =>
    request(`/saisons/${saisonId}/clubs`, { method: "POST", body: { club_id: clubId }, auth: true }),
  desinscrireClub: (saisonId, clubId) =>
    request(`/saisons/${saisonId}/clubs/${clubId}`, { method: "DELETE", auth: true }),
  joueurs: (clubId) => request(`/joueurs?limit=100${clubId ? `&club_id=${clubId}` : ""}`),
  creerJoueur: (payload) => request("/joueurs", { method: "POST", body: payload, auth: true }),
  joueur: (id) => request(`/joueurs/${id}`),
  joueurDetail: (id) => request(`/joueurs/${id}/detail`, { auth: true }),
  modifierJoueur: (id, payload) => request(`/joueurs/${id}`, { method: "PUT", body: payload, auth: true }),
  proposerJoueur: (id, champ, valeur) =>
    request(`/joueurs/${id}/proposer-modification`, {
      method: "POST",
      body: { champ, nouvelle_valeur: String(valeur) },
      auth: true,
    }),
  propositions: (joueurId) =>
    request(`/joueurs/propositions${joueurId ? `?joueur_id=${joueurId}` : ""}`, { auth: true }),
  approuverProposition: (id) =>
    request(`/joueurs/propositions/${id}/approuver`, { method: "PUT", auth: true }),
  audit: () => request("/audit", { auth: true }),
  matchs: (saisonId) => request(`/matchs?limit=100${saisonId ? `&saison_id=${saisonId}` : ""}`),
  match: (id) => request(`/matchs/${id}`),
  evenementsPublics: (id) => request(`/matchs/${id}/evenements-publics`),
  classement: (saisonId) => request(`/classement?saison_id=${saisonId}`),
  buteurs: (saisonId) => request(`/stats/meilleurs-buteurs?saison_id=${saisonId}&limit=10`),
  passeurs: (saisonId) => request(`/stats/meilleurs-passeurs?saison_id=${saisonId}&limit=10`),
  login: (email, mot_de_passe) => request("/auth/login", { method: "POST", body: { email, mot_de_passe } }),
  register: (nom_complet, email, mot_de_passe) =>
    request("/auth/register", { method: "POST", body: { nom_complet, email, mot_de_passe } }),
  me: () => request("/auth/me", { auth: true }),
  logout: (refresh_token) => request("/auth/logout", { method: "POST", body: { refresh_token } }),
  matchsGestion: (saisonId) =>
    request(`/matchs/gestion?limit=50${saisonId ? `&saison_id=${saisonId}` : ""}`, { auth: true }),
  matchGestion: (id) => request(`/matchs/gestion/${id}`, { auth: true }),
  evenementsStaff: (matchId) => request(`/matchs/${matchId}/evenements`, { auth: true }),
  fileValidation: () => request("/validation/evenements", { auth: true }),
  validerEvenement: (id) => request(`/validation/evenements/${id}`, { method: "PUT", auth: true }),
  rejeterEvenement: (id, commentaire) =>
    request(`/validation/evenements/${id}/rejeter`, { method: "PUT", auth: true, body: { commentaire } }),
  refuserArbitral: (id, motif, commentaire) =>
    request(`/validation/evenements/${id}/refuser`, {
      method: "PUT",
      auth: true,
      body: commentaire ? { motif, commentaire } : { motif },
    }),
  validerMatch: (id) => request(`/matchs/${id}/valider`, { method: "POST", auth: true }),
  creerMatch: (payload) => request("/matchs", { method: "POST", body: payload, auth: true }),
  changerStatut: (id, statut) =>
    request(`/matchs/${id}/statut?nouveau_statut=${encodeURIComponent(statut)}`, { method: "PUT", auth: true }),
  changerPeriode: (id, periode) =>
    request(`/matchs/${id}/periode?periode=${encodeURIComponent(periode)}`, { method: "PUT", auth: true }),
  forfait: (id, equipe) =>
    request(`/matchs/${id}/forfait?equipe_forfait=${encodeURIComponent(equipe)}`, { method: "POST", auth: true }),
  participations: (id) => request(`/matchs/${id}/participations`),
  ajouterParticipation: (id, payload) =>
    request(`/matchs/${id}/participations`, { method: "POST", body: payload, auth: true }),
  modifierParticipation: (id, pid, payload) =>
    request(`/matchs/${id}/participations/${pid}`, { method: "PUT", body: payload, auth: true }),
  retirerParticipation: (id, pid) =>
    request(`/matchs/${id}/participations/${pid}`, { method: "DELETE", auth: true }),
  saisirEvenement: (matchId, payload) =>
    request(`/matchs/${matchId}/evenements`, { method: "POST", body: payload, auth: true }),
};
