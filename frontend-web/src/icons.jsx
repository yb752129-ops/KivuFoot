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
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="9.35" fill="var(--paper)" stroke="var(--ink)" strokeWidth="1.45" />
      <polygon points="12,7.05 14.62,8.95 13.6,12.15 10.4,12.15 9.38,8.95" fill="var(--ink)" />
      <path fill="var(--ink)" d="M12 2.7 15.35 4.25 14.15 6.55 12 5.7 9.85 6.55 8.65 4.25Z" />
      <path fill="var(--ink)" d="M19.7 8.05 21 11.45 18.55 13.2 16.85 10.2 18.2 7.55Z" />
      <path fill="var(--ink)" d="M16.85 17.35 14.35 20.65 12 19.45 13.25 16.05 15.95 15.45Z" />
      <path fill="var(--ink)" d="M7.15 17.35 8.05 15.45 10.75 16.05 12 19.45 9.65 20.65Z" />
      <path fill="var(--ink)" d="M4.3 8.05 5.8 7.55 7.15 10.2 5.45 13.2 3 11.45Z" />
      <g fill="none" stroke="var(--ink)" strokeWidth="1.05" strokeLinejoin="round" strokeLinecap="round">
        <path d="M12 7.05V5.7" />
        <path d="M14.62 8.95 16.85 10.2" />
        <path d="M13.6 12.15 13.25 16.05" />
        <path d="M10.4 12.15 10.75 16.05" />
        <path d="M9.38 8.95 7.15 10.2" />
      </g>
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
