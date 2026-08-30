import { Navigate, Route, Routes } from "react-router-dom";
import { KivuProvider } from "./context.jsx";
import Layout from "./components/Layout.jsx";
import Home from "./pages/Home.jsx";
import Classement from "./pages/Classement.jsx";
import Matchs from "./pages/Matchs.jsx";
import MatchDetail from "./pages/MatchDetail.jsx";
import Clubs from "./pages/Clubs.jsx";
import ClubDetail from "./pages/ClubDetail.jsx";
import Joueur from "./pages/Joueur.jsx";
import Buteurs from "./pages/Buteurs.jsx";
import Login from "./pages/Login.jsx";
import Orga from "./pages/Orga.jsx";
import OrgaMatch from "./pages/OrgaMatch.jsx";
import { isAuthenticated } from "./api.js";

function Protegee({ children }) {
  return isAuthenticated() ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
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
        </Route>
        <Route path="/login" element={<Login />} />
        <Route
          path="/orga"
          element={
            <Protegee>
              <Orga />
            </Protegee>
          }
        />
        <Route
          path="/orga/matchs/:id"
          element={
            <Protegee>
              <OrgaMatch />
            </Protegee>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </KivuProvider>
  );
}
