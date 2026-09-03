import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { useKivu } from "../context.jsx";

const SOMMAIRE = [
  { to: "/", label: "Accueil", end: true, icon: "home" },
  { to: "/matchs", label: "Matchs", icon: "cal" },
  { to: "/classement", label: "Classement", icon: "tab" },
  { to: "/clubs", label: "Clubs", icon: "bouclier" },
];

function Ico({ name }) {
  const common = {
    viewBox: "0 0 24 24",
    className: "nav-ico",
    "aria-hidden": "true",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "1.6",
    strokeLinejoin: "round",
    strokeLinecap: "round",
  };
  if (name === "home") {
    return (
      <svg {...common}>
        <path d="M4 11.5 12 4l8 7.5V20h-6v-5H10v5H4z" />
      </svg>
    );
  }
  if (name === "cal") {
    return (
      <svg {...common}>
        <rect x="4" y="6" width="16" height="14" rx="1" />
        <path d="M8 4v4M16 4v4M4 11h16" />
      </svg>
    );
  }
  if (name === "tab") {
    return (
      <svg {...common}>
        <path d="M5 6h14M5 12h14M5 18h10" />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <path d="M12 3.5 19 7v5.2c0 4.3-2.8 7.4-7 8.8-4.2-1.4-7-4.5-7-8.8V7l7-3.5z" />
    </svg>
  );
}

function IconPersonne() {
  return (
    <svg viewBox="0 0 24 24" className="compte-ico" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="12" cy="8.2" r="3.1" />
      <path d="M5.6 19.2c.8-3.3 3.3-5.1 6.4-5.1s5.6 1.8 6.4 5.1" strokeLinecap="round" />
    </svg>
  );
}

function RechercheChamp() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  function go(e) {
    e.preventDefault();
    const t = q.trim();
    if (!t) return;
    navigate(`/recherche?q=${encodeURIComponent(t)}`);
  }
  return (
    <form className="mast-search" onSubmit={go} role="search">
      <input
        type="search"
        name="q"
        placeholder="Rechercher sur KivuFoot"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        aria-label="Rechercher sur KivuFoot"
      />
    </form>
  );
}

export default function Layout() {
  const { competition, error } = useKivu();
  const { prenom } = useAuth();
  return (
    <>
      <header className="masthead">
        <div className="masthead-inner">
          <div className="masthead-row">
            <NavLink to="/" className="wordmark">
              <span className="wordmark-name">KivuFoot</span>
              <span className="wordmark-place">Sud-Kivu</span>
            </NavLink>
            <RechercheChamp />
            <NavLink
              to="/compte"
              className="compte-personne"
              aria-label={prenom ? `Compte ${prenom}` : "Compte"}
            >
              <IconPersonne />
            </NavLink>
          </div>
          {competition?.est_demo && (
            <p className="demo-line">Données de démonstration</p>
          )}
        </div>
      </header>
      <div className="shell">
        {error && <p className="erreur">{error}</p>}
        <Outlet />
      </div>
      <nav className="bottom-nav" aria-label="Sommaire">
        {SOMMAIRE.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end}>
            <Ico name={item.icon} />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </>
  );
}
