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

export function Ballon({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.45"
      strokeLinejoin="round"
      strokeLinecap="round"
    >
      <circle cx="12" cy="12" r="9" />
      <polygon
        points="12,7.55 14.7,9.5 13.65,12.7 10.35,12.7 9.3,9.5"
        fill="currentColor"
        stroke="currentColor"
        strokeWidth="1.15"
      />
      <path d="M12 7.55V3.05" />
      <path d="M14.7 9.5 19.15 7.15" />
      <path d="M13.65 12.7 18.15 16.85" />
      <path d="M10.35 12.7 5.85 16.85" />
      <path d="M9.3 9.5 4.85 7.15" />
      <path d="M5.85 16.85 12 21 18.15 16.85" />
      <path d="M4.85 7.15 3.05 12.15 5.85 16.85" />
      <path d="M19.15 7.15 20.95 12.15 18.15 16.85" />
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
