import { api } from "./api.js";

export const MDP_DEMO = "ChangeMoiEnDemo123!";

export const COMPTES_TEST = [
  {
    label: "Collecteur",
    email: "collecteur.demo@example.com",
    porte: "/collecteur",
  },
  {
    label: "Club",
    email: "manager.demo@example.com",
    porte: "/club",
  },
  {
    label: "Coach",
    email: "coach.demo@example.com",
    porte: "/coach",
  },
  {
    label: "Organisateur",
    email: "orga.demo@example.com",
    porte: "/orga",
  },
  {
    label: "Admin",
    email: "admin.demo@example.com",
    porte: "/admin",
  },
];

export function porteDuRole(role) {
  if (role === "collecteur") return "/collecteur";
  if (role === "club_manager") return "/club";
  if (role === "coach") return "/coach";
  if (role === "organisateur") return "/orga";
  if (role === "admin") return "/admin";
  return "/";
}

export async function connecterCompteTest(email, applySession) {
  const tokens = await api.login(email, MDP_DEMO);
  return applySession(tokens);
}
