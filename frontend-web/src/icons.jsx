import { useId } from "react";

/** Langage visuel KivuFoot — pack icons-v2 (8 sept 2026).
 *  Événements publics : dessin SVG standard validé, badges proportionnels,
 *  et crampon bas incliné pour les passes décisives.
 */

const plein = {
  viewBox: "0 0 24 24",
  fill: "currentColor",
  "aria-hidden": "true",
};

const styleFait = (size = 18) => ({
  width: `${size}px`,
  height: `${size}px`,
  display: "block",
  flexShrink: 0,
  overflow: "visible",
});

function useBallonClipId() {
  const raw = useId();
  return `kf-ballon-clip-${raw.replace(/[^a-zA-Z0-9_-]/g, "")}`;
}

/** Ballon standard : cercle blanc r=11, clip r=10.6, six pentagones et traits #101612. */
function BallonDessin({ clipId }) {
  return (
    <>
      <defs>
        <clipPath id={clipId}><circle cx="12" cy="12" r="10.6" /></clipPath>
      </defs>
      <circle cx="12" cy="12" r="11" fill="#fff" />
      <g clipPath={`url(#${clipId})`} fill="#101612">
        <polygon points="12.0,8.7 15.1,11.0 13.9,14.7 10.1,14.7 8.9,11.0" />
        <polygon points="12.0,4.0 7.9,1.0 9.5,-3.8 14.5,-3.8 16.1,1.0" />
        <polygon points="19.6,9.5 21.2,4.7 26.2,4.7 27.8,9.5 23.7,12.5" />
        <polygon points="16.7,18.5 21.8,18.5 23.3,23.3 19.2,26.3 15.1,23.3" />
        <polygon points="7.3,18.5 8.9,23.3 4.8,26.3 0.7,23.3 2.2,18.5" />
        <polygon points="4.4,9.5 0.3,12.5 -3.8,9.5 -2.2,4.7 2.8,4.7" />
      </g>
      <g clipPath={`url(#${clipId})`} fill="none" stroke="#101612" strokeWidth="0.9" strokeLinecap="round">
        <line x1="12.0" y1="8.7" x2="12.0" y2="4.0" />
        <line x1="15.1" y1="11.0" x2="19.6" y2="9.5" />
        <line x1="13.9" y1="14.7" x2="16.7" y2="18.5" />
        <line x1="10.1" y1="14.7" x2="7.3" y2="18.5" />
        <line x1="8.9" y1="11.0" x2="4.4" y2="9.5" />
      </g>
      <circle cx="12" cy="12" r="10.6" fill="none" stroke="#101612" strokeWidth="0.8" />
    </>
  );
}

export function Ballon({ className, size = 18 }) {
  const clipId = useBallonClipId();
  return (
    <svg viewBox="0 0 24 24" className={className} style={styleFait(size)} aria-hidden="true" focusable="false">
      <BallonDessin clipId={clipId} />
    </svg>
  );
}

function BallonBadge({ className, size = 18, couleur, marque }) {
  const clipId = useBallonClipId();
  const scored = marque === "check";
  return (
    <svg viewBox="0 0 25 25" className={className} style={styleFait(size)} overflow="visible" aria-hidden="true" focusable="false">
      <BallonDessin clipId={clipId} />
      <g>
        <circle cx="19.6" cy="19.6" r="4.9" fill={couleur} stroke="#0b1410" strokeWidth="1.6" />
        {scored ? (
          <path d="M17.3 19.7 L19.1 21.5 L22 17.8" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        ) : (
          <path d="M17.6 17.6 L21.6 21.6 M21.6 17.6 L17.6 21.6" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" />
        )}
      </g>
    </svg>
  );
}

/** Crampon bas incliné exact, sans tige montante. */
export function Botte({ className, size = 14 }) {
  return (
    <svg viewBox="0 0 24 24" className={className} width={size} height={size} fill="none" aria-hidden="true" focusable="false" style={{ width: `${size}px`, height: `${size}px`, verticalAlign: "middle", flexShrink: 0, display: "inline-block" }}>
      <g transform="rotate(-14 12 12)">
        <path d="M2.4 10.6 C2.4 9.5 3.3 8.9 4.3 9.2 L7.8 10.2 C8.7 10.5 9.4 11.2 10.4 11.7 C12.5 12.7 14.8 12.9 17 13.7 C19.9 14.7 22 15.4 22 17 V17.4 H2.4 Z" fill="#B9C3BE" />
        <path d="M2.4 18.1 H22 V19 H2.4 Z" fill="#B9C3BE" />
        <path d="M4 19 h2 l-.5 2.4 h-1 z M8.2 19 h2 l-.4 2.4 h-1 z M14.4 19 h2 l-.4 2.4 h-1 z M18.8 19 h2 l-.5 2.4 h-1 z" fill="#B9C3BE" />
        <path d="M10.6 11.9 l1.3 -1.6 M12.7 12.7 l1.3 -1.6 M14.8 13.2 l1.3 -1.5" stroke="#0b1410" strokeWidth="1" strokeLinecap="round" />
      </g>
    </svg>
  );
}

/** CSC : même ballon standard ; le suffixe « csc » est porté par le texte. */
export function IcoCsc({ className, size = 18 }) {
  return <Ballon className={className} size={size} />;
}

/** Penalty raté : ballon standard noir et blanc + badge rouge exact. */
export function IcoRefuse({ className, size = 18 }) {
  return <BallonBadge className={className} size={size} couleur="#E5484D" marque="cross" />;
}

/** Penalty marqué : ballon standard noir et blanc + badge vert exact. */
export function IcoPenalty({ className, size = 18 }) {
  return <BallonBadge className={className} size={size} couleur="#22C55E" marque="check" />;
}

/** Remplacement, formule SofaScore : flèche rouge sort, flèche verte entre. */
export function IcoRemplacement({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} style={styleFait(18)} aria-hidden="true">
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

/** Loupe en trait : bouton rond du masthead (maquette). */
export function IcoRecherche({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" aria-hidden="true">
      <circle cx="10.6" cy="10.6" r="6.4" />
      <path d="M15.4 15.4 20 20" />
    </svg>
  );
}

/** Cloche en trait : bouton rond du masthead (maquette). Ouvre les matchs en direct. */
export function IcoCloche({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 4c-3.6 0-6 2.6-6 6.2v3.2l-1.7 2.4h15.4L18 13.4v-3.2C18 6.6 15.6 4 12 4Z" />
      <path d="M10.2 18.8a1.9 1.9 0 0 0 3.6 0" />
    </svg>
  );
}

/** Écusson crème à monogramme, comme les boucliers de la maquette. */
export function Ecu({ initiales, className }) {
  return (
    <svg className={className} viewBox="0 0 44 50" aria-hidden="true">
      <path d="M22 1 43 8v18c0 12-9 20-21 23C10 46 1 38 1 26V8Z" fill="var(--cream, #EFEDE6)" />
      <text x="22" y="31" textAnchor="middle" fontSize="15" fontWeight="700" fill="#0F3D2E" fontFamily="inherit">{initiales}</text>
    </svg>
  );
}

/** Épingle de lieu en trait, pour les lignes du bulletin (maquette). */
export function IcoEpingle({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 21c-4.4-5.2-6.8-8.6-6.8-12a6.8 6.8 0 0 1 13.6 0c0 3.4-2.4 6.8-6.8 12Z" />
      <circle cx="12" cy="9" r="2.4" />
    </svg>
  );
}
