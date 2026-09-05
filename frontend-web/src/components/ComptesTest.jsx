import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { COMPTES_TEST, connecterCompteTest, porteDuRole } from "../portes.js";

export default function ComptesTest() {
  const nav = useNavigate();
  const { user, applySession, logout } = useAuth();
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");

  async function entrer(c) {
    setErr("");
    setBusy(c.email);
    try {
      if (user) await logout();
      const me = await connecterCompteTest(c.email, applySession);
      nav(porteDuRole(me?.role), { replace: true });
    } catch (ex) {
      setErr(ex.message || "Connexion démo impossible.");
    } finally {
      setBusy("");
    }
  }

  return (
    <>
      <div className="section-head">
        <h2>Comptes de test</h2>
      </div>
      <p className="lead">Un tap connecte et ouvre la porte. Pas un compte lecteur.</p>
      {err && <p className="erreur">{err}</p>}
      {COMPTES_TEST.map((c) => (
        <button
          key={c.email}
          type="button"
          className="avenir-row"
          disabled={Boolean(busy)}
          style={{ width: "100%", background: "transparent", border: 0, borderBottom: "1px solid var(--rule)", textAlign: "left", cursor: "pointer" }}
          onClick={() => entrer(c)}
        >
          <span className="avenir-noms">
            <span>{c.label}</span>
            <span className="meta-line">
              {busy === c.email ? "Connexion…" : `${c.email} → ${c.porte}`}
            </span>
          </span>
        </button>
      ))}
    </>
  );
}
