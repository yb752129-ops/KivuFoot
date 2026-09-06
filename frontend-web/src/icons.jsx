/** Langage visuel KivuFoot */

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
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
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

export function FlecheIn({ className }) {
  return (
    <svg {...base} className={className}>
      <path d="M12 19V5M5.5 11.5 12 5l6.5 6.5" />
    </svg>
  );
}

export function FlecheOut({ className }) {
  return (
    <svg {...base} className={className}>
      <path d="M12 5v14M5.5 12.5 12 19l6.5-6.5" />
    </svg>
  );
}

export function Botte({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.55"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M5 16h10.4c1.45 0 3.35-.55 4.35-2.35" />
      <path d="M6.2 16v2.15M10.5 16v2.15M14.6 16v1.9" />
    </svg>
  );
}

export function Carton({ couleur = "jaune", className }) {
  const fill = couleur === "rouge" ? "#dc2626" : "#eab308";
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <rect x="7" y="4" width="10" height="16" rx="1.5" fill={fill} />
    </svg>
  );
}
