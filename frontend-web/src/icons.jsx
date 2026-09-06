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

const tailleFaits = {
  width: "1.15rem",
  height: "1.15rem",
  display: "block",
  flexShrink: 0,
};

export function Ballon({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={tailleFaits}
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9.5" />
      <path d="M12 2.5a9.5 9.5 0 0 1 0 19" />
      <path d="M12 2.5a9.5 9.5 0 0 0 0 19" />
      <path d="M2.5 12h19" />
      <path d="M7 5.5l5 3 5-3" />
      <path d="M7 18.5l5-3 5 3" />
    </svg>
  );
}

export function Botte({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.55"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{
        width: "1rem",
        height: "1rem",
        verticalAlign: "middle",
        marginRight: "0.35rem",
        flexShrink: 0,
      }}
      aria-hidden="true"
    >
      <path d="M5 16h10.4c1.45 0 3.35-.55 4.35-2.35.55-1 .5-2.15 0-3.1L18.4 8.7c-.4-1-1.3-1.65-2.35-1.65h-3.5L8.3 5.2H5.2V16z" />
      <path d="M6.2 16v2.15M10.5 16v2.15M14.6 16v1.9" />
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
