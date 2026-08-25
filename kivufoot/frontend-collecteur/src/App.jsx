import { useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Login from "./pages/Login";
import Matchs from "./pages/Matchs";
import SaisieEvenement from "./pages/SaisieEvenement";
import { isAuthenticated } from "./lib/api";
import { demarrerSyncPeriodique } from "./lib/sync";

function RouteProtegee({ children }) {
  return isAuthenticated() ? children : <Navigate to="/login" replace />;
}

export default function App() {
  useEffect(() => {
    const arreter = demarrerSyncPeriodique();
    return arreter;
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/matchs"
          element={
            <RouteProtegee>
              <Matchs />
            </RouteProtegee>
          }
        />
        <Route
          path="/matchs/:matchId/saisie"
          element={
            <RouteProtegee>
              <SaisieEvenement />
            </RouteProtegee>
          }
        />
        <Route path="*" element={<Navigate to={isAuthenticated() ? "/matchs" : "/login"} replace />} />
      </Routes>
    </BrowserRouter>
  );
}
