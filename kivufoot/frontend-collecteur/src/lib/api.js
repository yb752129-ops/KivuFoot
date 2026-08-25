const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

function getAccessToken() {
  return localStorage.getItem("kivufoot_access_token");
}

export function setTokens({ access_token, refresh_token }) {
  localStorage.setItem("kivufoot_access_token", access_token);
  localStorage.setItem("kivufoot_refresh_token", refresh_token);
}

export function clearTokens() {
  localStorage.removeItem("kivufoot_access_token");
  localStorage.removeItem("kivufoot_refresh_token");
}

export function isAuthenticated() {
  return Boolean(getAccessToken());
}

async function request(path, options = {}) {
  const token = getAccessToken();
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || "Erreur réseau");
  }
  if (res.status === 204) return null;
  return res.json();
}

export async function login(email, motDePasse) {
  const tokens = await request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, mot_de_passe: motDePasse }),
  });
  setTokens(tokens);
  return tokens;
}

export async function fetchMatchsDisponibles() {
  // Le collecteur voit ses matchs assignés via la route staff (nécessite un rôle autorisé).
  return request("/matchs?limit=50");
}

export async function pushEvenements(items) {
  return request("/sync/push", { method: "POST", body: JSON.stringify({ items }) });
}

export async function pullMiseAJour(depuis) {
  const qs = depuis ? `?depuis=${encodeURIComponent(depuis)}` : "";
  return request(`/sync/pull${qs}`);
}

export default { login, fetchMatchsDisponibles, pushEvenements, pullMiseAJour, isAuthenticated, clearTokens };
