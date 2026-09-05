import { Ballon, Carton } from "../icons.jsx";
import { clockFromMatch, estPeriodeUn, formatMinute, libelleFeuille, MOTIF_REFUS } from "../display.js";

function Ico({ e }) {
  if (e.type === "carton_jaune") return <Carton couleur="jaune" />;
  if (e.type === "carton_rouge" && e.source === "deuxieme_jaune") {
    return (
      <span className="feuille-cartons">
        <Carton couleur="rouge" />
        <Carton couleur="jaune" />
      </span>
    );
  }
  if (e.type === "carton_rouge") return <Carton couleur="rouge" />;
  const ballon = e.type === "but" || e.type === "but_contre_son_camp"
    || (e.type === "penalty" && e.resultat !== "rate" && e.resultat !== "raté");
  if (ballon) {
    return (
      <span className="feuille-ballon-wrap">
        <Ballon className="fait-ballon" />
        {e.refuse && <span className="fait-rate" aria-hidden="true">×</span>}
      </span>
    );
  }
  if (e.type === "penalty") return <span className="fait-rate" aria-hidden="true">×</span>;
  return null;
}

function LigneFait({ e, nom }) {
  const joueur = nom(e.joueur_id);
  const second = e.joueur_secondaire_id ? nom(e.joueur_secondaire_id) : "";
  const motif = MOTIF_REFUS[e.motif_refus] || e.motif_refus;
  const libelle = libelleFeuille(e);
  const sub = e.type === "remplacement";
  const assist = !e.refuse && e.type === "but" && second;
  const titre = sub
    ? "Remplacement"
    : e.refuse
      ? `${libelle} · ${joueur}${motif ? ` (${motif})` : ""}`
      : `${libelle} · ${joueur}`;

  return (
    <li className={`feuille-ligne${e.refuse ? " is-refuse" : ""}`}>
      <span className="feuille-min">{formatMinute(e.minute, e.minute_additionnelle)}</span>
      <span className="feuille-ico" aria-hidden="true"><Ico e={e} /></span>
      <div className="feuille-txt">
        <p className="fait-ligne"><span className="fait-nom">{titre}</span></p>
        {sub && (
          <p className="fait-assist">
            Sort : {joueur || "à compléter"} → Entre : {second || "à compléter"}
          </p>
        )}
        {assist && <p className="fait-assist">Passe décisive · {second}</p>}
      </div>
    </li>
  );
}

function LigneCycle({ minute, texte }) {
  return (
    <li className="feuille-ligne is-cycle">
      <span className="feuille-min">{minute}</span>
      <p className="feuille-cycle">{texte}</p>
    </li>
  );
}

function minuteFin(match) {
  if (!match) return "";
  const t = match.ended_at ? new Date(match.ended_at).getTime() : Date.now();
  const c = clockFromMatch(match, t);
  if (c.min > 90) return formatMinute(90, c.min - 90);
  if (c.periode !== "2" && c.min > 45) return formatMinute(45, c.min - 45);
  if (c.min) return formatMinute(c.min, 0);
  return "";
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

  if (!chrono.length && !montreHt && !montreFin && !montreCoup) {
    return <p className="empty">Aucun événement rendu public pour ce match.</p>;
  }

  return (
    <ul className="feuille-apercu">
      {montreCoup && <LigneCycle minute="1′" texte="Coup d’envoi" />}
      {p1.map((e) => <LigneFait key={e.id} e={e} nom={nom} />)}
      {montreHt && <LigneCycle minute="45′" texte="Mi-temps" />}
      {montreP2 && <LigneCycle minute="" texte="Début de la seconde période" />}
      {p2.map((e) => <LigneFait key={e.id} e={e} nom={nom} />)}
      {montreFin && <LigneCycle minute={minuteFin(match)} texte="Fin du match" />}
    </ul>
  );
}
