/** Langage visuel KivuFoot — pack icons-v2 (8 sept 2026).
 *  Glyphes d’événements PLEINS, standard LiveScore validé par Yves le 8 sept 09:15.
 *  Remplacement = formule SofaScore (flèche rouge sort, flèche verte entre).
 *  Aucun VAR. Nav/UI restent en traits jusqu’au pack portes (13–14 sept).
 */

const plein = {
  viewBox: "0 0 24 24",
  fill: "currentColor",
  "aria-hidden": "true",
};

const styleFait = { width: "1.25rem", height: "1.25rem", display: "block", flexShrink: 0 };

/** Ballon plein : cercle noir, pentagone et encoches blanches. */
export function Ballon({ className }) {
  return (
    <svg {...plein} className={className} style={styleFait} fillRule="nonzero">
      <path d="M2.00,12.00 a10.00,10.00 0 1,1 20.00,0 a10.00,10.00 0 1,1 -20.00,0 Z M8.58,10.89 L9.88,14.91 L14.12,14.91 L15.42,10.89 L12.00,8.40 Z M15.97,3.51 a2.20,2.20 0 1,0 4.40,0 a2.20,2.20 0 1,0 -4.40,0 Z M19.79,15.24 a2.20,2.20 0 1,0 4.40,0 a2.20,2.20 0 1,0 -4.40,0 Z M9.80,22.50 a2.20,2.20 0 1,0 4.40,0 a2.20,2.20 0 1,0 -4.40,0 Z M-0.19,15.24 a2.20,2.20 0 1,0 4.40,0 a2.20,2.20 0 1,0 -4.40,0 Z M3.63,3.51 a2.20,2.20 0 1,0 4.40,0 a2.20,2.20 0 1,0 -4.40,0 Z" />
    </svg>
  );
}

/** Crampon plein de profil : tige, pointe, semelle. */
export function Botte({ className }) {
  return (
    <svg {...plein} className={className} fillRule="nonzero"
      style={{ width: "1.35rem", height: "1.35rem", verticalAlign: "middle", marginRight: "0.4rem", flexShrink: 0, display: "inline-block" }}>
      <path d="M8.0,2.8 h6.2 v6.4 c0,0.9 0.4,1.5 1.2,1.9 l3.6,1.8 c1.5,0.7 2.3,1.9 2.3,3.4 v1.9 H5.8 v-7.6 c0,-1.1 0.4,-1.9 1.1,-2.6 l1.1,-1.1 Z" />
    </svg>
  );
}

/** But contre son camp : ballon cerclé. */
export function IcoCsc({ className }) {
  return (
    <svg {...plein} className={className} style={styleFait} fillRule="nonzero">
      <path d="M1.00,12.00 a11.00,11.00 0 1,1 22.00,0 a11.00,11.00 0 1,1 -22.00,0 Z M5.00,12.00 a7.00,7.00 0 1,1 14.00,0 a7.00,7.00 0 1,1 -14.00,0 Z M3.40,12.00 a8.60,8.60 0 1,0 17.20,0 a8.60,8.60 0 1,0 -17.20,0 Z M9.72,11.26 L10.59,13.94 L13.41,13.94 L14.28,11.26 L12.00,9.60 Z" />
    </svg>
  );
}

/** But refusé / penalty raté : ballon + badge croix. Jamais de mention VAR. */
export function IcoRefuse({ className }) {
  return (
    <svg {...plein} className={className} style={styleFait} fillRule="nonzero">
      <path d="M2.40,9.60 a7.20,7.20 0 1,1 14.40,0 a7.20,7.20 0 1,1 -14.40,0 Z M12.90,17.80 a4.90,4.90 0 1,1 9.80,0 a4.90,4.90 0 1,1 -9.80,0 Z M11.50,17.80 a6.30,6.30 0 1,0 12.60,0 a6.30,6.30 0 1,0 -12.60,0 Z M12.90,17.80 a4.90,4.90 0 1,1 9.80,0 a4.90,4.90 0 1,1 -9.80,0 Z M7.22,8.83 L8.13,11.62 L11.07,11.62 L11.98,8.83 L9.60,7.10 Z M12.27,3.45 a1.80,1.80 0 1,0 3.60,0 a1.80,1.80 0 1,0 -3.60,0 Z M15.03,11.95 a1.80,1.80 0 1,0 3.60,0 a1.80,1.80 0 1,0 -3.60,0 Z M7.80,17.20 a1.80,1.80 0 1,0 3.60,0 a1.80,1.80 0 1,0 -3.60,0 Z M0.57,11.95 a1.80,1.80 0 1,0 3.60,0 a1.80,1.80 0 1,0 -3.60,0 Z M3.33,3.45 a1.80,1.80 0 1,0 3.60,0 a1.80,1.80 0 1,0 -3.60,0 Z M16.42,14.65 L20.95,19.18 L19.18,20.95 L14.65,16.42 Z M20.95,16.42 L16.42,20.95 L14.65,19.18 L19.18,14.65 Z" />
    </svg>
  );
}

/** Penalty : ballon posé sur son point. */
export function IcoPenalty({ className }) {
  return (
    <svg {...plein} className={className} style={styleFait} fillRule="nonzero">
      <path d="M4.40,9.60 a7.60,7.60 0 1,1 15.20,0 a7.60,7.60 0 1,1 -15.20,0 Z M8.20,18.60 h7.60 v2.20 h-7.60 Z M9.43,8.77 L10.41,11.78 L13.59,11.78 L14.57,8.77 L12.00,6.90 Z M14.90,3.13 a1.80,1.80 0 1,0 3.60,0 a1.80,1.80 0 1,0 -3.60,0 Z M17.81,12.07 a1.80,1.80 0 1,0 3.60,0 a1.80,1.80 0 1,0 -3.60,0 Z M10.20,17.60 a1.80,1.80 0 1,0 3.60,0 a1.80,1.80 0 1,0 -3.60,0 Z M2.59,12.07 a1.80,1.80 0 1,0 3.60,0 a1.80,1.80 0 1,0 -3.60,0 Z M5.50,3.13 a1.80,1.80 0 1,0 3.60,0 a1.80,1.80 0 1,0 -3.60,0 Z" />
    </svg>
  );
}

/** Remplacement, formule SofaScore : flèche rouge sort, flèche verte entre. */
export function IcoRemplacement({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} style={styleFait} aria-hidden="true">
      <path d="M9.00,6.30 h10.60 v2.60 h-10.60 Z M9.40,4.20 L9.40,11.00 L4.20,7.60 Z" fill="#EF4444" />
      <path d="M4.40,15.10 h10.60 v2.60 h-10.60 Z M14.60,13.00 L14.60,19.80 L19.80,16.40 Z" fill="#10B981" />
    </svg>
  );
}

/** Sifflet plein : pour les séparateurs de période. */
export function IcoSifflet({ className }) {
  return (
    <svg {...plein} className={className} fillRule="nonzero"
      style={{ width: "1rem", height: "1rem", display: "inline-block", verticalAlign: "-0.15rem", marginRight: "0.35rem" }}>
      <path d="M7.90,14.00 a6.30,6.30 0 1,1 12.60,0 a6.30,6.30 0 1,1 -12.60,0 Z M3.40,7.60 h8.20 v4.60 h-8.20 Z M11.90,14.00 a2.30,2.30 0 1,0 4.60,0 a2.30,2.30 0 1,0 -4.60,0 Z M5.20,9.00 v1.80 h4.40 v-1.80 Z" />
    </svg>
  );
}

/** Silhouette photo officielle : cadre plein, personne évidée. */
export function IcoPhoto({ className }) {
  return (
    <svg {...plein} className={className} fillRule="nonzero"
      style={{ width: "1.5rem", height: "1.5rem", display: "block", flexShrink: 0 }}>
      <path d="M5.5,3 h13 a2.5,2.5 0 0 1 2.5,2.5 v13 a2.5,2.5 0 0 1 -2.5,2.5 h-13 a2.5,2.5 0 0 1 -2.5,-2.5 v-13 a2.5,2.5 0 0 1 2.5,-2.5 Z M8.90,9.80 a3.10,3.10 0 1,0 6.20,0 a3.10,3.10 0 1,0 -6.20,0 Z M17.4,18.4 c0,-3.4 -2.4,-5.4 -5.4,-5.4 c-3.0,0 -5.4,2.0 -5.4,5.4 Z" />
    </svg>
  );
}

export function IcoHome({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" aria-hidden="true">
      <path d="M4 11.5 12 4l8 7.5V20h-6v-5H10v5H4z" />
    </svg>
  );
}

export function IcoCalendrier({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" aria-hidden="true">
      <rect x="4" y="6" width="16" height="14" rx="1" />
      <path d="M8 4v4M16 4v4M4 11h16" />
    </svg>
  );
}

export function IcoClassement({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" aria-hidden="true">
      <path d="M5 6h14M5 12h14M5 18h10" />
    </svg>
  );
}

export function IcoBouclier({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" aria-hidden="true">
      <path d="M12 3.5 19 7v5.2c0 4.3-2.8 7.4-7 8.8-4.2-1.4-7-4.5-7-8.8V7l7-3.5z" />
    </svg>
  );
}

export function IcoPersonne({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="12" cy="8.2" r="3.1" />
      <path d="M5.6 19.2c.8-3.3 3.3-5.1 6.4-5.1s5.6 1.8 6.4 5.1" strokeLinecap="round" />
    </svg>
  );
}

/** Cartons : inchangés, approuvés par Yves. Rendus par CSS (kf-carton). */
export function Carton({ couleur = "jaune", className }) {
  return (
    <span
      className={`kf-carton kf-carton-${couleur}${className ? ` ${className}` : ""}`}
      aria-hidden="true"
    />
  );
}

export function FlecheIn({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" aria-hidden="true">
      <path d="M12 19V5M6.5 10.5 12 5l5.5 5.5" />
    </svg>
  );
}

export function FlecheOut({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" aria-hidden="true">
      <path d="M12 5v14M6.5 13.5 12 19l5.5-5.5" />
    </svg>
  );
}
