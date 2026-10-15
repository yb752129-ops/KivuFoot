import { Ballon, Botte, Carton, FlecheIn, FlecheOut, IcoPenalty, IcoRefuse } from "../icons.jsx";
import { formatMinute, labelEvenement, MOTIF_REFUS } from "../display.js";

function penaltyRate(e) {
  return e.type === "penalty" && (e.resultat === "rate" || e.resultat === "raté");
}

function Ico({ e }) {
  if (e.type === "carton_jaune") return <Carton couleur="jaune" />;
  if (e.type === "carton_rouge") return <Carton couleur="rouge" />;
  if (e.type === "remplacement") return null;
  if (e.refuse || penaltyRate(e)) return <IcoRefuse className="fait-ballon" size={18} />;
  if (e.type === "penalty") return <IcoPenalty className="fait-ballon" size={18} />;
  if (e.type === "but" || e.type === "but_contre_son_camp") return <Ballon className="fait-ballon" size={18} />;
  return null;
}

export default function FaitMatch({ e, nom, children }) {
  const min = formatMinute(e.minute, e.minute_additionnelle);
  const refuse = Boolean(e.refuse);
  const joueur = nom(e.joueur_id);
  const second = e.joueur_secondaire_id ? nom(e.joueur_secondaire_id) : "";
  const motif = MOTIF_REFUS[e.motif_refus] || e.motif_refus;
  const sub = e.type === "remplacement";
  const csc = e.type === "but_contre_son_camp";
  const penalty = e.type === "penalty";
  const assist = !refuse && e.type === "but" && second;
  const deuxJaune = e.type === "carton_rouge" && e.source === "deuxieme_jaune";

  const libelle = penaltyRate(e)
    ? "Penalty raté"
    : penalty
      ? "Penalty"
      : csc
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
        ) : csc ? (
          <p className="fait-ligne fait-csc-ligne">
            <span className="fait-csc-copy">
              <span className="fait-nom">{joueur}</span>
              <span className="fait-csc-suffix">csc</span>
            </span>
          </p>
        ) : penalty ? (
          <p className="fait-ligne fait-stacked">
            <span className="fait-tag">{libelle}</span>
            <span className="fait-nom">{joueur}</span>
          </p>
        ) : (
          <p className="fait-ligne">
            {libelle && libelle !== "But" && <span className="fait-tag">{libelle}</span>}
            <span className="fait-nom">{joueur}</span>
          </p>
        )}
        {assist && (
          <p className="fait-assist">
            <Botte className="fait-botte" size={14} />
            <span>{second}</span>
          </p>
        )}
        {refuse && (
          <p className="fait-refus">
            {penalty ? "Penalty refusé" : "But refusé"}
            {motif ? ` [${motif}]` : ""}
          </p>
        )}
        {children}
      </div>
    </li>
  );
}
