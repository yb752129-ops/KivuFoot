import { Ballon, Carton, FlecheIn, FlecheOut } from "../icons.jsx";
import { formatMinute, labelEvenement, MOTIF_REFUS } from "../display.js";

function Ico({ e }) {
  if (e.type === "carton_jaune") return <Carton couleur="jaune" />;
  if (e.type === "carton_rouge") return <Carton couleur="rouge" />;
  if (e.type === "but" || e.type === "but_contre_son_camp") return <Ballon className="fait-ballon" />;
  if (e.type === "penalty" && e.resultat !== "rate" && e.resultat !== "raté") {
    return <Ballon className="fait-ballon" />;
  }
  return null;
}

export default function FaitMatch({ e, nom, children }) {
  const min = formatMinute(e.minute, e.minute_additionnelle);
  const refuse = Boolean(e.refuse);
  const joueur = nom(e.joueur_id);
  const second = e.joueur_secondaire_id ? nom(e.joueur_secondaire_id) : "";
  const motif = MOTIF_REFUS[e.motif_refus] || e.motif_refus;
  const penaltyRate = e.type === "penalty" && (e.resultat === "rate" || e.resultat === "raté");
  const sub = e.type === "remplacement";
  const assist = !refuse && e.type === "but" && second;
  const deuxJaune = e.type === "carton_rouge" && e.source === "deuxieme_jaune";

  const libelle = penaltyRate
    ? "Penalty raté"
    : e.type === "penalty"
      ? "Penalty"
      : e.type === "but_contre_son_camp"
        ? "CSC"
        : deuxJaune
          ? "Rouge (2e jaune)"
          : sub
            ? null
            : labelEvenement(e);

  return (
    <li className={`fait${refuse ? " is-refuse" : ""}${e.equipe_concernee === "exterieur" ? " is-away" : ""}`}>
      <span className="fait-min">{min}</span>
      <span className="fait-ico" aria-hidden="true"><Ico e={e} /></span>
      <div className="fait-corps">
        {sub ? (
          <p className="fait-sub">
            <span className="fait-in">
              <FlecheIn className="fait-fleche" /> {second || "Entrant"}
            </span>
            <span className="fait-out">
              <FlecheOut className="fait-fleche" /> {joueur || "Sortant"}
            </span>
          </p>
        ) : (
          <p className="fait-ligne">
            {libelle && libelle !== "But" && <span className="fait-tag">{libelle}</span>}
            <span className="fait-nom">{joueur}</span>
          </p>
        )}
        {assist && (
          <p className="fait-assist">Passe décisive · {second}</p>
        )}
        {refuse && (
          <p className="fait-refus">
            {e.type === "penalty" ? "Penalty refusé" : "But refusé"}
            {motif ? ` — ${motif}` : ""}
          </p>
        )}
        {children}
      </div>
    </li>
  );
}
