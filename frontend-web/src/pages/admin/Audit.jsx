import { useEffect, useState } from "react";
import { api } from "../../api.js";
import { formatJour } from "../../display.js";

const ACTION = {
  INSERT: "Création",
  UPDATE: "Modification",
  DELETE: "Suppression",
  VALIDATE: "Validation",
  REJECT: "Rejet",
  MERGE: "Fusion",
};

export default function AdminAudit() {
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.audit().then(setRows).catch((e) => setErr(e.message));
  }, []);

  return (
    <section className="hero">
      <p className="kicker">Administration</p>
      <h1>Audit</h1>
      <p className="lead">Toute action critique. Le public ne voit pas ça.</p>
      {err && <p className="erreur">{err}</p>}
      {rows.length === 0 && !err && <p className="empty">Rien dans l’audit.</p>}
      {rows.map((e) => (
        <div key={e.id} className="id-row">
          <span>{ACTION[e.action] || e.action}</span>
          <strong>
            {e.table_name} #{e.record_id}
            {e.created_at ? ` · ${formatJour(e.created_at)}` : ""}
          </strong>
        </div>
      ))}
    </section>
  );
}
