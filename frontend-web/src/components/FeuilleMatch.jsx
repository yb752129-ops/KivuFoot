import { Link } from "react-router-dom";
import { labelPoste, stripDemo } from "../display.js";

function LigneJoueur({ j }) {
  return (
    <Link to={`/joueurs/${j.id}`} className="feuille-ligne">
      <span className="feuille-photo" aria-hidden="true">
        {j.photo_url ? <img src={j.photo_url} alt="" /> : (j.nom_complet || "?").charAt(0)}
      </span>
      <span className="feuille-nom">{j.nom_complet}</span>
      <span className="feuille-num">{j.numero ?? "–"}</span>
      <span className="feuille-poste">{labelPoste(j.poste) || "Poste"}</span>
    </Link>
  );
}

function BlocEquipe({ bloc, logoUrl }) {
  const nom = stripDemo(bloc.club_nom) || "Équipe à nommer";
  const logo = logoUrl || bloc.logo_url;
  const titulaires = bloc.titulaires || [];
  const banc = bloc.banc || [];
  const staff = bloc.staff;
  return (
    <section className="feuille-equipe">
      <header className="feuille-tete">
        <span className="feuille-logo" aria-hidden="true">
          {logo ? <img className="logo-libre" src={logo} alt="" /> : (nom || "?").charAt(0)}
        </span>
        <span className="feuille-club">
          <strong>{nom}</strong>
          {bloc.formation && <span className="feuille-formation">{bloc.formation}</span>}
        </span>
      </header>
      {titulaires.length === 0 && banc.length === 0 ? (
        <p className="feuille-vide">Composition non publiée.</p>
      ) : (
        <>
          <h3 className="feuille-section">Entraîneur</h3>
          {staff ? (
            <span className="feuille-coach">
              <span className="feuille-photo" aria-hidden="true">
                {staff.photo_url ? <img src={staff.photo_url} alt="" /> : (staff.nom_complet || "?").charAt(0)}
              </span>
              <span className="feuille-nom">{staff.nom_complet}</span>
              <span className="feuille-poste">{staff.role_label || posteStaff(staff.role)}</span>
            </span>
          ) : (
            <p className="feuille-vide">Entraîneur à compléter.</p>
          )}
          <h3 className="feuille-section">Titulaires</h3>
          {titulaires.map((j) => <LigneJoueur key={j.id} j={j} />)}
          <h3 className="feuille-section">Remplaçants</h3>
          {banc.length === 0 ? <p className="feuille-vide">Aucun remplaçant déclaré.</p> : banc.map((j) => <LigneJoueur key={j.id} j={j} />)}
        </>
      )}
    </section>
  );
}

function posteStaff(r) {
  const t = String(r || "").replace(/_/g, " ").trim();
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : "";
}

export default function FeuilleMatch({ compo, logos = {} }) {
  if (!compo) return <p className="empty">Chargement…</p>;
  return (
    <div className="feuille">
      <BlocEquipe bloc={compo.domicile} logoUrl={logos.domicile} />
      <BlocEquipe bloc={compo.exterieur} logoUrl={logos.exterieur} />
    </div>
  );
}
