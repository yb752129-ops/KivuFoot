import { Ballon, Carton, FlecheIn, FlecheOut } from "../icons.jsx";
import { estPeriodeUn, formatMinute, labelEvenement } from "../display.js";

function Ico({ e }) {
  if (e.type === "carton_jaune") return <Carton couleur="jaune" />;
  if (e.type === "carton_rouge") return <Carton couleur="rouge" />;
  if (e.type === "but" || e.type === "but_contre_son_camp") return <Ballon className="fait-ballon" />;
  if (e.type === "penalty" && e.resultat !== "rate" && e.resultat !== "raté") {
    return <Ballon className="fait-ballon" />;
  }
  return null;
}

function Texte({ e, nom }) {
  const joueur = nom(e.joueur_id);
  const second = e.joueur_secondaire_id ? nom(e.joueur_secondaire_id) : "";
  const penaltyRate = e.type === "penalty" && (e.resultat === "rate" || e.resultat === "raté");
  const sub = e.type === "remplacement";
  const assist = !e.refuse && e.type === "but" && second;
  const libelle = penaltyRate
    ? "Penalty raté"
    : e.type === "penalty"
      ? "Penalty"
      : e.type === "but_contre_son_camp"
        ? "CSC"
        : e.type === "carton_rouge" && e.source === "deuxieme_jaune"
          ? "Rouge (2e jaune)"
          : sub
            ? null
            : labelEvenement(e);

  return (
    <div className={`feuille-txt${e.refuse ? " is-refuse" : ""}`}>
      <span className="feuille-ico" aria-hidden="true"><Ico e={e} /></span>
      <div>
        {sub ? (
          <p className="fait-sub">
            <span className="fait-in"><FlecheIn className="fait-fleche" /> {second || "à compléter"}</span>
            <span className="fait-out"><FlecheOut className="fait-fleche" /> {joueur || "à compléter"}</span>
          </p>
        ) : (
          <p className="fait-ligne">
            {libelle && libelle !== "But" && <span className="fait-tag">{libelle}</span>}
            {penaltyRate && <span className="fait-rate" aria-hidden="true">×</span>}
            <span className="fait-nom">{joueur}</span>
          </p>
        )}
        {assist && <p className="fait-assist">Passe · {second}</p>}
      </div>
    </div>
  );
}

export default function FeuilleApercu({ faits, nom, match }) {
  const chrono = [...(faits || [])].sort(
    (a, b) =>
      (a.minute || 0) - (b.minute || 0)
      || (a.minute_additionnelle || 0) - (b.minute_additionnelle || 0)
      || (a.id || 0) - (b.id || 0),
  );
  const p1 = chrono.filter(estPeriodeUn);
  const p2 = chrono.filter((e) => !estPeriodeUn(e));
  const montreHt = match?.periode === "mi_temps" || match?.periode === "2" || match?.statut === "termine" || match?.statut === "valide";
  const montreFin = match?.statut === "termine" || match?.statut === "valide";

  function lignes(list) {
    return list.map((e) => {
      const away = e.equipe_concernee === "exterieur";
      return (
        <li key={e.id} className="feuille-row">
          <div className="feuille-dom">{away ? null : <Texte e={e} nom={nom} />}</div>
          <span className="feuille-min">{formatMinute(e.minute, e.minute_additionnelle)}</span>
          <div className="feuille-ext">{away ? <Texte e={e} nom={nom} /> : null}</div>
        </li>
      );
    });
  }

  if (!chrono.length && !montreHt && !montreFin) {
    return <p className="empty">Aucun événement rendu public pour ce match.</p>;
  }

  return (
    <ul className="feuille-apercu">
      {lignes(p1)}
      {montreHt && (
        <li className="feuille-break">Mi-temps</li>
      )}
      {lignes(p2)}
      {montreFin && (
        <li className="feuille-break">
          Fin {match.score_domicile}–{match.score_exterieur}
        </li>
      )}
    </ul>
  );
}
