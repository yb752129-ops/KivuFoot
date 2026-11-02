import { Navigate } from "react-router-dom";

// Conserve les anciens favoris tout en dirigeant vers le nouveau filtre MATCHS.
export default function PhaseFinale() {
  return <Navigate to="/matchs?filtre=phase-finale&tour=barrage" replace />;
}
