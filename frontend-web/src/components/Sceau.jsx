/** Sceau-ballon KivuFoot — colophon, pas une icône d’app. */
export default function Sceau({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <circle
        cx="16"
        cy="16"
        r="14.15"
        stroke="currentColor"
        strokeWidth="1.7"
      />
      <polygon
        fill="var(--stamp)"
        points="16 10.65 21.09 14.35 19.14 20.33 12.86 20.33 10.91 14.35"
      />
      <path
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
        strokeLinecap="round"
        d="M16 10.65 21.76 8.07 21.09 14.35
           M21.09 14.35 25.32 19.03 19.14 20.33
           M19.14 20.33 16 25.8 12.86 20.33
           M12.86 20.33 6.68 19.03 10.91 14.35
           M10.91 14.35 10.24 8.07 16 10.65"
      />
    </svg>
  );
}
