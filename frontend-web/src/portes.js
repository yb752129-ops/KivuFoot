import { isClubRole } from "./roles.js";

export function porteDuRole(role) {
  if (role === "collecteur") return "/collecteur";
  if (isClubRole(role)) return "/club";
  if (role === "organisateur") return "/orga";
  if (role === "admin") return "/admin";
  return "/";
}
