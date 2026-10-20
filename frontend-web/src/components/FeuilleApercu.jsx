import { Ballon, Botte, Carton, IcoPenalty, IcoRefuse } from "../icons.jsx";
import { scorePublicVisible } from "./PublicDesign.jsx";
import { estPeriodeUn, formatMinute, labelEvenement, MOTIF_REFUS } from "../display.js";

function estPenaltyRate(e) {
  return e.type === "penalty" && (e.resultat === "rate" || e.resultat === "raté");
}

function RemplacementBadge({ direction }) {
  const entrant = direction === "in";
  return (
    <svg
      className={`feuille-remplacement-badge ${entrant ? "is-in" : "is-out"}`}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="12" cy="12" r="10" />
      <path d={entrant ? "M7 12h9m-3.5-3.5L16 12l-3.5 3.5" : "M17 12H8m3.5-3.5L8 12l3.5 3.5"} />
    </svg>
  );
}

function Ico({ e, size = 18 }) {
  if (e.type === "carton_jaune") return <Carton couleur="jaune" />;
  if (e.type === "carton_rouge") return <Carton couleur="rouge" />;
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
  const carton = e.type === "carton_jaune" || e.type === "carton_rouge";
  const assist = !e.refuse && e.type === "but" && second;
  const motif = MOTIF_REFUS[e.motif_refus] || e.motif_refus;
  const libelle = labelEvenement(e);
  const tag = !carton && !sub && !csc && libelle && libelle !== "But" ? libelle : null;

  return (
    <div className={`feuille-txt${e.refuse ? " is-refuse" : ""}${sub ? " is-remplacement" : ""}`}>
      {!sub && <span className="feuille-ico" aria-hidden="true"><Ico e={e} /></span>}
      <div className="feuille-copy">
        {sub ? (
          <div className="fait-sub">
            <span className="fait-player fait-in">
              <span className="fait-player-name">{second || "à compléter"}</span>
              <RemplacementBadge direction="in" />
            </span>
            <span className="fait-player fait-out">
              <span className="fait-player-name">{joueur || "à compléter"}</span>
              <RemplacementBadge direction="out" />
            </span>
          </div>
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

function scoreMiTemps(events) {
  let domicile = 0;
  let exterieur = 0;
  for (const e of events) {
    if (e.refuse || e.score_comptabilise === false) continue;
    const side = e.equipe_concernee === "exterieur" ? "exterieur" : "domicile";
    const goal = e.type === "but"
      || e.type === "but_contre_son_camp"
      || (e.type === "penalty" && e.resultat !== "rate" && e.resultat !== "raté");
    if (!goal) continue;
    const target = e.type === "but_contre_son_camp"
      ? (side === "domicile" ? "exterieur" : "domicile")
      : side;
    if (target === "domicile") domicile += 1;
    else exterieur += 1;
  }
  return `${domicile}–${exterieur}`;
}

function MarqueurPeriode({ children }) {
  return (
    <li className="feuille-break">
      <span className="feuille-break-line" aria-hidden="true" />
      <span className="feuille-break-label">{children}</span>
      <span className="feuille-break-line" aria-hidden="true" />
    </li>
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
  const coupEnvoi = Boolean(match?.started_at);
  const miTemps = Boolean(match?.paused_at || match?.periode === "mi_temps" || match?.periode === "2" || match?.periode_started_at);
  const deuxiemePeriode = Boolean(match?.periode_started_at || match?.periode === "2" || p2.length > 0);
  const finMatch = Boolean(match?.ended_at || ["termine", "valide"].includes(match?.statut));
  const scorePause = miTemps && p1.some((e) => (
    !e.refuse
    && (e.type === "but" || e.type === "but_contre_son_camp" || e.type === "penalty")
  )) ? scoreMiTemps(p1) : "";
  const aMarqueurs = coupEnvoi || miTemps || deuxiemePeriode || finMatch;

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
      const minute = (
        <span className="feuille-min">
          {e.minute_connue === false ? "—" : formatMinute(e.minute, e.minute_additionnelle)}
        </span>
      );
      return (
        <li key={e.id} className={classes}>
          <div className="feuille-dom">
            {!estExterieur && (
              <div className="feuille-event-side">
                {minute}
                <Texte e={e} nom={nom} />
              </div>
            )}
          </div>
          <div className="feuille-ext">
            {estExterieur && (
              <div className="feuille-event-side feuille-event-side-away">
                <Texte e={e} nom={nom} />
                {minute}
              </div>
            )}
          </div>
        </li>
      );
    });
  }

  if (!scorePublicVisible(match)) {
    return <p className="empty">Le match n'a pas encore commencé.</p>;
  }

  if (!chrono.length && !aMarqueurs) {
    return <p className="empty">Aucun événement rendu public pour ce match.</p>;
  }

  return (
    <ul className="feuille-apercu">
      {coupEnvoi && <MarqueurPeriode>Coup d’envoi</MarqueurPeriode>}
      {lignes(p1)}
      {miTemps && <MarqueurPeriode>Mi-temps{scorePause ? ` · ${scorePause}` : ""}</MarqueurPeriode>}
      {deuxiemePeriode && <MarqueurPeriode>2e période</MarqueurPeriode>}
      {lignes(p2)}
      {finMatch && <MarqueurPeriode>Fin du match · {match.score_domicile}–{match.score_exterieur}</MarqueurPeriode>}
    </ul>
  );
}
