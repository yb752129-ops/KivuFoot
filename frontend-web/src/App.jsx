import { Navigate, Route, Routes } from "react-router-dom";
import { KivuProvider } from "./context.jsx";
import Layout from "./components/Layout.jsx";
import OrgaLayout from "./components/OrgaLayout.jsx";
import CollecteurLayout from "./components/CollecteurLayout.jsx";
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
import CollecteurMatchs from "./pages/collecteur/Matchs.jsx";
import CollecteurMatch from "./pages/collecteur/Match.jsx";
import ClubLayout from "./components/ClubLayout.jsx";
import ClubVue from "./pages/club/Vue.jsx";
import ClubEffectif from "./pages/club/Effectif.jsx";
import ClubJoueur from "./pages/club/Joueur.jsx";
import ClubMatchs from "./pages/club/Matchs.jsx";
import { AuthProvider, useAuth } from "./auth.jsx";
import { isAuthenticated } from "./api.js";

function Porte({ roles, children }) {
  const { user } = useAuth();
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  if (user && !roles.includes(user.role)) {
    if (user.role === "collecteur") return <Navigate to="/collecteur" replace />;
    if (user.role === "organisateur") return <Navigate to="/orga" replace />;
    if (user.role === "club_manager") return <Navigate to="/club" replace />;
    return <Navigate to="/" replace />;
  }
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
              <Porte roles={["organisateur", "admin"]}>
                <OrgaLayout />
              </Porte>
            }
          >
            <Route index element={<OrgaVue />} />
            <Route path="equipes" element={<OrgaEquipes />} />
            <Route path="equipes/:id" element={<OrgaEquipe />} />
            <Route path="calendrier" element={<OrgaCalendrier />} />
            <Route path="matchs" element={<OrgaMatchsListe />} />
            <Route path="matchs/:id" element={<OrgaMatch />} />
          </Route>
          <Route
            path="/collecteur"
            element={
              <Porte roles={["collecteur", "admin"]}>
                <CollecteurLayout />
              </Porte>
            }
          >
            <Route index element={<CollecteurMatchs />} />
            <Route path="matchs/:id" element={<CollecteurMatch />} />
          </Route>
          <Route
            path="/club"
            element={
              <Porte roles={["club_manager"]}>
                <ClubLayout />
              </Porte>
            }
          >
            <Route index element={<ClubVue />} />
            <Route path="effectif" element={<ClubEffectif />} />
            <Route path="effectif/:id" element={<ClubJoueur />} />
            <Route path="matchs" element={<ClubMatchs />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </KivuProvider>
    </AuthProvider>
  );
}
