import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api.js";
import { useAuth } from "../../auth.jsx";
import { clubName, useKivu } from "../../context.jsx";
import { stripDemo } from "../../display.js";
import { fmtQuand, STATUT_MATCH } from "../orga/saison.js";

export default function CoachMatch() {
  const { id } = useParams();
  const { user } = useAuth();
  const { clubsById } = useKivu();
  const clubId = user?.club_id;
  const [match, setMatch] = useState(null);
  const [compo, setCompo] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!clubId) return;
    api.match(id).then(setMatch).catch((e) => setErr(e.message));
    api.composition(id).then(setCompo).catch(() => setCompo(null));
  }, [id, clubId]);

  if (!clubId) return <p className="empty">Aucun club rattaché.</p>;
  if (!match) return <p className="empty">{err || "Chargement…"}</p>;

  const home = stripDemo(clubName(clubsById, match.equipe_domicile_id));
  const away = stripDemo(clubName(clubsById, match.equipe_exterieur_id));
  const cote = clubId === match.equipe_domicile_id ? "domicile" : "exterieur";
  const autreCote = cote === "domicile" ? "exterieur" : "domicile";
  const verrouille = match.locked || ["en_cours", "termine", "valide"].includes(match.statut);
  const bloc = compo?.[cote];
  const autreBloc = compo?.[autreCote];

  return (
    <section className="hero">
      <p className="kicker"><Link to="/coach/matchs">← Matchs</Link></p>
      <h1>{home} · {away}</h1>
      <p className="lead">
        {[STATUT_MATCH[match.statut] || match.statut, fmtQuand(match.date_heure)].filter(Boolean).join(" · ")}
      </p>
      {err && <p className="erreur">{err}</p>}
      {verrouille && (
        <p className="empty">Match verrouillé — la feuille ne peut plus être modifiée.</p>
      )}

      <div className="sheet" style={{ marginTop: "1rem" }}>
        <div className="avenir-row">
          <span className="avenir-noms">
            <span>Feuille de composition</span>
            <span className="meta-line">
              {bloc
                ? `Titulaires ${(bloc.titulaires || []).length}/11 · Banc ${(bloc.banc || []).length}/${compo?.max_remplacants ?? "—"}${bloc.formation ? ` · ${bloc.formation}` : ""}${bloc.staff ? ` · ${bloc.staff.nom_complet || ""}` : ""}`
                : "Pas encore de feuille"}
            </span>
          </span>
          <Link className="btn btn-primary" to={`/coach/matchs/${id}/composition`}>
            {verrouille ? "Voir la feuille" : "Composition"}
          </Link>
        </div>
      </div>

      <div className="section-head" style={{ marginTop: "1.2rem" }}>
        <h2>{autreCote === "domicile" ? home : away}</h2>
      </div>
      <p className="lead">L’autre composition. Vous ne la posez pas.</p>
      {!autreBloc || ((autreBloc.titulaires || []).length === 0 && (autreBloc.banc || []).length === 0) ? (
        <p className="empty">Composition à compléter</p>
      ) : (
        <p className="empty">
          Titulaires {(autreBloc.titulaires || []).length} · Banc {(autreBloc.banc || []).length}
          {autreBloc.formation ? ` · ${autreBloc.formation}` : ""}
        </p>
      )}

      <p className="id-out">
        <Link to={`/matchs/${id}`}>Voir le match public</Link>
      </p>
    </section>
  );
}
