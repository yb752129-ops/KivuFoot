import { Ballon, Botte, Carton, IcoPenalty, IcoRefuse, IcoRemplacement, IcoSifflet } from "../icons.jsx";
import { scorePublicVisible } from "./PublicDesign.jsx";
import { estPeriodeUn, formatMinute, labelEvenement, MOTIF_REFUS } from "../display.js";

function estPenaltyRate(e) {
  return e.type === "penalty" && (e.resultat === "rate" || e.resultat === "raté");
}

function Ico({ e, size = 18 }) {
  if (e.type === "carton_jaune") return <Carton couleur="jaune" />;
  if (e.type === "carton_rouge") return <Carton couleur="rouge" />;
  if (e.type === "remplacement") return <IcoRemplacement className="fait-ballon" />;
  if (e.refuse || estPenaltyRate(e)) return <IcoRefuse className="fait-ballon" size={size} />;
  if (e.type === "penalty") return <IcoPenalty className="fait-ballon" size={size} />;
  if (e.type === "but" || e.type === "but_contre_son_camp") return <Ballon className="fait-ballon" size={size} />;
  return null;
}

function Texte({ e, nom }) {
  const joueur = nom(e.joueur_id);
  const second = e.joueur_secondaire_id ? nom(e.joueur_secondaire_id) : "";
  const sub = e.type === "remplacement";
  const csc = e.type === "but_contre_son_camp";
  const penalty = e.type === "penalty";
  const assist = !e.refuse && e.type === "but" && second;
  const motif = MOTIF_REFUS[e.motif_refus] || e.motif_refus;
  const libelle = labelEvenement(e);
  const tag = !csc && libelle && libelle !== "But" ? libelle : null;

  return (
    <div className={`feuille-txt${e.refuse ? " is-refuse" : ""}`}>
      <span className="feuille-ico" aria-hidden="true"><Ico e={e} /></span>
      <div>
        {sub ? (
          <p className="fait-sub">
            <span className="fait-in">{second || "à compléter"}</span>
            <span className="fait-out">{joueur || "à compléter"}</span>
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
            {tag && <span className="fait-tag">{tag}</span>}
            <span className="fait-nom">{joueur}</span>
          </p>
        )}
        {assist && (
          <p className="fait-assist">
            <Botte className="fait-botte" size={14} />
            <span>{second}</span>
          </p>
        )}
        {e.refuse && (
          <p className="fait-refus">
            {e.type === "penalty" ? "Penalty refusé" : "But refusé"}
            {motif ? ` [${motif}]` : ""}
          </p>
        )}
      </div>
    </div>
  );
}

function Legende() {
  return (
    <section className="feuille-legende" aria-label="Légende des événements">
      <h2>Légende</h2>
      <div className="feuille-legende-grid">
        <span className="feuille-legende-item"><Ballon size={16} />But</span>
        <span className="feuille-legende-item"><IcoPenalty size={16} />Penalty marqué</span>
        <span className="feuille-legende-item"><Ballon size={16} />csc = but contre son camp</span>
        <span className="feuille-legende-item"><IcoRefuse size={16} />Penalty raté</span>
        <span className="feuille-legende-item"><Carton couleur="jaune" />Carton</span>
        <span className="feuille-legende-item"><Carton couleur="rouge" />Carton rouge</span>
        <span className="feuille-legende-item"><IcoRemplacement className="feuille-legende-remplacement" />Remplacement</span>
        <span className="feuille-legende-item"><Botte size={14} />Passe décisive</span>
      </div>
    </section>
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
  const montreCoup = Boolean(match?.started_at);
  const montreHt = match?.periode === "mi_temps" || match?.periode === "2" || p2.length > 0;
  const montreP2 = match?.periode === "2" || p2.length > 0;
  const montreFin = match?.statut === "termine" || match?.statut === "valide";

  function lignes(list) {
    return list.map((e) => {
      // equipe_concernee est la référence backend : aucune inversion CSC.
      const estExterieur = e.equipe_concernee === "exterieur";
      const hasAssist = !e.refuse && e.type === "but" && Boolean(e.joueur_secondaire_id);
      const classes = [
        "feuille-row",
        hasAssist && "has-assist",
        e.type === "but_contre_son_camp" && "is-csc",
      ].filter(Boolean).join(" ");
      return (
        <li key={e.id} className={classes}>
          <div className="feuille-dom">{estExterieur ? null : <Texte e={e} nom={nom} />}</div>
          <span className="feuille-min">{e.minute_connue === false ? "—" : formatMinute(e.minute, e.minute_additionnelle)}</span>
          <div className="feuille-ext">{estExterieur ? <Texte e={e} nom={nom} /> : null}</div>
        </li>
      );
    });
  }

  if (!scorePublicVisible(match)) {
    return <p className="empty">Le match n'a pas encore commencé.</p>;
  }

  if (!chrono.length && !montreHt && !montreFin && !montreCoup) {
    return <p className="empty">Aucun événement rendu public pour ce match.</p>;
  }

  return (
    <>
      <Legende />
      <ul className="feuille-apercu">
        {montreCoup && <li className="feuille-break"><IcoSifflet />Coup d’envoi</li>}
        {lignes(p1)}
        {montreHt && <li className="feuille-break"><IcoSifflet />Mi-temps</li>}
        {montreP2 && <li className="feuille-break"><IcoSifflet />2e période</li>}
        {lignes(p2)}
        {montreFin && (
          <li className="feuille-break">
            <IcoSifflet />Fin {match.score_domicile}–{match.score_exterieur}
          </li>
        )}
      </ul>
    </>
  );
}
