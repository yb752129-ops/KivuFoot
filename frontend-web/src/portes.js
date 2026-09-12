export function porteDuRole(role) {
  if (role === "collecteur") return "/collecteur";
  if (role === "club_manager") return "/club";
  if (role === "coach") return "/coach";
  if (role === "organisateur") return "/orga";
  if (role === "admin") return "/admin";
  return "/";
}
