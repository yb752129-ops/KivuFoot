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

function BlocEquipe({ bloc }) {
  const nom = stripDemo(bloc.club_nom) || "Équipe à nommer";
  const titulaires = bloc.titulaires || [];
  const banc = bloc.banc || [];
  const staff = bloc.staff;
  return (
    <section className="feuille-equipe">
      <header className="feuille-tete">
        <span className="feuille-logo" aria-hidden="true">
          {bloc.logo_url ? <img className="logo-libre" src={bloc.logo_url} alt="" /> : (nom || "?").charAt(0)}
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
          <h3 className="feuille-section">Titulaires</h3>
          {titulaires.map((j) => <LigneJoueur key={j.id} j={j} />)}
          <h3 className="feuille-section">Banc</h3>
          {banc.length === 0 ? <p className="feuille-vide">Aucun remplaçant déclaré.</p> : banc.map((j) => <LigneJoueur key={j.id} j={j} />)}
          <h3 className="feuille-section">Entraîneur</h3>
          {staff ? (
            <span className="feuille-coach">
              <span className="feuille-photo" aria-hidden="true">
                {staff.photo_url ? <img src={staff.photo_url} alt="" /> : (staff.full_name || "?").charAt(0)}
              </span>
              <span className="feuille-nom">{staff.full_name}</span>
              <span className="feuille-poste">{staff.role_label || staff.role || ""}</span>
            </span>
          ) : (
            <p className="feuille-vide">Entraîneur à compléter.</p>
          )}
        </>
      )}
    </section>
  );
}

export default function FeuilleMatch({ compo }) {
  if (!compo) return <p className="empty">Chargement…</p>;
  return (
    <div className="feuille">
      <BlocEquipe bloc={compo.domicile} />
      <BlocEquipe bloc={compo.exterieur} />
    </div>
  );
}
