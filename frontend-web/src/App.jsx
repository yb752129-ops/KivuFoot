import { Navigate, Route, Routes } from "react-router-dom";
import { KivuProvider } from "./context.jsx";
import Layout from "./components/Layout.jsx";
import OrgaLayout from "./components/OrgaLayout.jsx";
import Home from "./pages/Home.jsx";
import Classement from "./pages/Classement.jsx";
import Matchs from "./pages/Matchs.jsx";
import MatchDetail from "./pages/MatchDetail.jsx";
import Clubs from "./pages/Clubs.jsx";
import ClubDetail from "./pages/ClubDetail.jsx";
import Joueur from "./pages/Joueur.jsx";
import Buteurs from "./pages/Buteurs.jsx";
import Login from "./pages/Login.jsx";
import Compte from "./pages/Compte.jsx";
import Recherche from "./pages/Recherche.jsx";
import OrgaVue from "./pages/orga/Vue.jsx";
import OrgaEquipes from "./pages/orga/Equipes.jsx";
import OrgaEquipe from "./pages/orga/Equipe.jsx";
import OrgaCalendrier from "./pages/orga/Calendrier.jsx";
import OrgaMatchsListe from "./pages/orga/MatchsListe.jsx";
import OrgaMatch from "./pages/OrgaMatch.jsx";
import { AuthProvider, useAuth } from "./auth.jsx";
import { isAuthenticated } from "./api.js";

function Protegee({ children }) {
  const { user } = useAuth();
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  if (user?.role === "supporter") return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <KivuProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/classement" element={<Classement />} />
            <Route path="/matchs" element={<Matchs />} />
            <Route path="/matchs/:id" element={<MatchDetail />} />
            <Route path="/clubs" element={<Clubs />} />
            <Route path="/clubs/:id" element={<ClubDetail />} />
            <Route path="/joueurs/:id" element={<Joueur />} />
            <Route path="/buteurs" element={<Buteurs />} />
            <Route path="/compte" element={<Compte />} />
            <Route path="/recherche" element={<Recherche />} />
          </Route>
          <Route path="/login" element={<Login />} />
          <Route
            path="/orga"
            element={
              <Protegee>
                <OrgaLayout />
              </Protegee>
            }
          >
            <Route index element={<OrgaVue />} />
            <Route path="equipes" element={<OrgaEquipes />} />
            <Route path="equipes/:id" element={<OrgaEquipe />} />
            <Route path="calendrier" element={<OrgaCalendrier />} />
            <Route path="matchs" element={<OrgaMatchsListe />} />
            <Route path="matchs/:id" element={<OrgaMatch />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </KivuProvider>
    </AuthProvider>
  );
}
