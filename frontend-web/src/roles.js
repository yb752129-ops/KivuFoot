// Shared frontend definition of the unified club portal permission set.
// Coach accounts are converted to club by migration 0024; all club features
// live under /club. club_manager remains a backend compatibility alias.
export const CLUB_ROLES = Object.freeze(["club", "club_manager"]);

export function isClubRole(role) {
  return CLUB_ROLES.includes(role);
}
