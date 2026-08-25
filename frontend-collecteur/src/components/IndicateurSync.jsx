import { useLiveQuery } from "dexie-react-hooks";
import { db } from "../lib/db";

export default function IndicateurSync() {
  const enAttente = useLiveQuery(() => db.evenementsLocaux.where("statutSync").equals("local").count(), []);
  const conflits = useLiveQuery(() => db.evenementsLocaux.where("statutSync").equals("conflit").count(), []);
  const rejetes = useLiveQuery(() => db.evenementsLocaux.where("statutSync").equals("rejete").count(), []);
  const enLigne = navigator.onLine;

  return (
    <div className="indicateur-sync" title={enLigne ? "Connecté" : "Hors-ligne"}>
      <span className={`pastille ${enLigne ? "en-ligne" : "hors-ligne"}`} />
      {enAttente > 0 && <span className="badge badge-attente">{enAttente} en attente</span>}
      {rejetes > 0 && <span className="badge badge-rejete">{rejetes} rejeté(s)</span>}
      {conflits > 0 && <span className="badge badge-conflit">{conflits} conflit(s)</span>}
    </div>
  );
}
