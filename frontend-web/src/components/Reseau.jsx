import { useEffect, useState } from "react";

export default function Reseau() {
  const [perdu, setPerdu] = useState(() => navigator.onLine === false);

  useEffect(() => {
    const off = () => setPerdu(true);
    const on = () => setPerdu(false);
    window.addEventListener("offline", off);
    window.addEventListener("online", on);
    return () => {
      window.removeEventListener("offline", off);
      window.removeEventListener("online", on);
    };
  }, []);

  if (!perdu) return null;
  return (
    <div className="reseau-perdu" role="status" aria-live="polite">
      Hors connexion — KivuFoot se reconnectera tout seul au retour du réseau.
    </div>
  );
}
