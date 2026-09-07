/** Langage visuel KivuFoot — traits, pas Lucide, pas d’emoji. */

const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: "1.6",
  strokeLinejoin: "round",
  strokeLinecap: "round",
  "aria-hidden": "true",
};

/** Vrai ballon de football (panneaux), lisible à la taille d’un fait. */
export function Ballon({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 32 32"
      width="20"
      height="20"
      style={{ width: "1.25rem", height: "1.25rem", display: "block", flexShrink: 0 }}
      aria-hidden="true"
    >
      <circle cx="16" cy="16" r="14.2" fill="var(--paper, #f4f1ea)" stroke="currentColor" strokeWidth="1.7" />
      <polygon points="16,10.2 19.7,12.9 18.25,17.35 13.75,17.35 12.3,12.9" fill="currentColor" />
      <path fill="currentColor" d="M11.2 2.9h9.6l1.4 3.6-6.2 1.8-6.2-1.8Z" />
      <path fill="currentColor" d="M27.6 10.3 29.4 15.4 25.4 18.4 23.3 13.6 25.6 9.6Z" />
      <path fill="currentColor" d="M22.7 23.4 18.6 28.8 16 27.1 17.6 22.1 21.8 21.2Z" />
      <path fill="currentColor" d="M9.3 23.4 10.2 21.2 14.4 22.1 16 27.1 13.4 28.8Z" />
      <path fill="currentColor" d="M4.4 10.3 6.4 9.6 8.7 13.6 6.6 18.4 2.6 15.4Z" />
      <g fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinejoin="round" strokeLinecap="round">
        <path d="M16 10.2V8.3" />
        <path d="M19.7 12.9 23.3 13.6" />
        <path d="M18.25 17.35 17.6 22.1" />
        <path d="M13.75 17.35 14.4 22.1" />
        <path d="M12.3 12.9 8.7 13.6" />
      </g>
    </svg>
  );
}

/** Crampon de profil : tige, pointe, semelle, 4 crampons. */
export function Botte({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width="22"
      height="22"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{
        width: "1.35rem",
        height: "1.35rem",
        verticalAlign: "middle",
        marginRight: "0.4rem",
        flexShrink: 0,
        display: "inline-block",
      }}
      aria-hidden="true"
    >
      <path d="M4.2 8.2V16.4h12.4c1.1 0 2.35-.35 3.15-1.35.55-.7.7-1.55.55-2.35L19.3 9.4c-.3-.85-1.1-1.4-2-1.4h-3.15L11.4 5.2H6.1c-.9 0-1.9.7-1.9 1.7z" />
      <path d="M6.4 16.4v3.1M10.2 16.4v3.1M14 16.4v2.85M17.4 16.4v2.45" />
    </svg>
  );
}

export function IcoHome({ className }) {
  return (
    <svg {...base} className={className}>
      <path d="M4 11.5 12 4l8 7.5V20h-6v-5H10v5H4z" />
    </svg>
  );
}

export function IcoCalendrier({ className }) {
  return (
    <svg {...base} className={className}>
      <rect x="4" y="6" width="16" height="14" rx="1" />
      <path d="M8 4v4M16 4v4M4 11h16" />
    </svg>
  );
}

export function IcoClassement({ className }) {
  return (
    <svg {...base} className={className}>
      <path d="M5 6h14M5 12h14M5 18h10" />
    </svg>
  );
}

export function IcoBouclier({ className }) {
  return (
    <svg {...base} className={className}>
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
    <svg {...base} className={className}>
      <path d="M12 19V5M6.5 10.5 12 5l5.5 5.5" />
    </svg>
  );
}

export function FlecheOut({ className }) {
  return (
    <svg {...base} className={className}>
      <path d="M12 5v14M6.5 13.5 12 19l5.5-5.5" />
    </svg>
  );
}
