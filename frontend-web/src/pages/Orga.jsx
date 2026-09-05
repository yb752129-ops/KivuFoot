import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, clearTokens } from "../api.js";
import { clubName, useKivu } from "../context.jsx";
import { formatMinute, stripDemo } from "../display.js";

const STATUT = {
  programme: "Programmé",
  en_cours: "En cours",
  termine: "Terminé",
  valide: "Validé",
  conteste: "Contesté",
};

function isoDepuisDateHeure(date, heure) {
  if (!date || !heure) throw new Error("Indiquez la date et l’heure du match.");
  const d = new Date(`${date}T${heure}`);
  if (Number.isNaN(d.getTime())) throw new Error("Date ou heure invalide.");
  return d.toISOString();
}

function fmtQuand(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

export default function Orga() {
  const nav = useNavigate();
  const {
    saison,
    clubs,
    saisonClubs,
    clubsById,
    competition,
    choisirCompetition,
    rechargerCompetitions,
    rechargerClubs,
    chargerClubsSaison,
  } = useKivu();
  const equipes = saisonClubs ?? [];
  const [me, setMe] = useState(null);
  const [file, setFile] = useState([]);
  const [matchs, setMatchs] = useState([]);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [nomComp, setNomComp] = useState("");
  const [typeComp, setTypeComp] = useState("tournoi");
  const [nomSaison, setNomSaison] = useState("");
  const [dateDebut, setDateDebut] = useState("");
  const [nomEquipe, setNomEquipe] = useState("");
  const [villeEquipe, setVilleEquipe] = useState("");
  const [stadeEquipe, setStadeEquipe] = useState("");
  const [domId, setDomId] = useState("");
  const [extId, setExtId] = useState("");
  const [dateMatch, setDateMatch] = useState("");
  const [heureMatch, setHeureMatch] = useState("");
  const [stadeMatch, setStadeMatch] = useState("");
  const [journee, setJournee] = useState("");
  const [rejetId, setRejetId] = useState(null);
  const [rejetCom, setRejetCom] = useState("");

  async function load() {
    setErr("");
    try {
      const user = await api.me();
      setMe(user);
      const [ev, ms] = await Promise.all([
        api.fileValidation(),
        saison ? api.matchsGestion(saison.id) : Promise.resolve([]),
      ]);
      setFile(ev);
      setMatchs(ms);
    } catch (e) {
      setErr(e.message);
      if (e.status === 401) {
        clearTokens();
        nav("/login", { replace: true });
      }
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [saison]);

  function nom(id) {
    return stripDemo(clubName(clubsById, id));
  }

  async function creerCompetitionTerrain(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      const nom = nomComp.trim();
      if (!nom) throw new Error("Indiquez le nom de la compétition.");
      const comp = await api.creerCompetition({
        nom,
        type: typeComp,
        saison_label: nomSaison.trim() || null,
        est_demo: false,
      });
      await api.creerSaison({
        competition_id: comp.id,
        nom: nomSaison.trim() || null,
        date_debut: dateDebut || null,
        club_ids: [],
      });
      const list = await rechargerCompetitions();
      await choisirCompetition(comp.id, list || []);
      setMsg("Compétition créée. Elle n’est pas une DEMO.");
      setNomComp("");
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  async function creerEquipe(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      if (!saison) throw new Error("Choisissez d’abord une compétition avec une saison.");
      const nom = nomEquipe.trim();
      const ville = villeEquipe.trim();
      if (!nom) throw new Error("Indiquez le nom de l’équipe.");
      if (!ville) throw new Error("Indiquez la ville ou le département.");
      const club = await api.creerClub({
        nom,
        ville,
        stade: stadeEquipe.trim() || null,
      });
      await api.inscrireClub(saison.id, club.id);
      await rechargerClubs();
      await chargerClubsSaison(saison.id);
      setMsg("Équipe inscrite.");
      setNomEquipe("");
      setVilleEquipe("");
      setStadeEquipe("");
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  async function programmerMatch(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      if (!saison) throw new Error("Choisissez d’abord une compétition avec une saison.");
      const d = Number(domId);
      const x = Number(extId);
      if (!d || !x) throw new Error("Choisissez les deux équipes.");
      if (d === x) throw new Error("Une équipe ne peut pas jouer contre elle-même.");
      const domicile = equipes.find((c) => c.id === d) || clubsById[d];
      await api.creerMatch({
        saison_id: saison.id,
        journee: journee.trim().slice(0, 20) || null,
        date_heure: isoDepuisDateHeure(dateMatch, heureMatch),
        stade: stadeMatch.trim() || domicile?.stade || null,
        equipe_domicile_id: d,
        equipe_exterieur_id: x,
      });
      setMsg("Match programmé.");
      setDomId("");
      setExtId("");
      setStadeMatch("");
      setJournee("");
      await load();
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  async function preparerTest() {
    setBusy(true);
    setErr("");
    try {
      const kadutu = clubs.find((c) => /kadutu/i.test(c.nom));
      const ibanda = clubs.find((c) => /ibanda/i.test(c.nom));
      if (!kadutu || !ibanda || !saison) throw new Error("Clubs DEMO introuvables.");
      for (const c of [kadutu, ibanda]) {
        try {
          await api.inscrireClub(saison.id, c.id);
        } catch {
          /* déjà inscrit */
        }
      }
      const deja = matchs.find(
        (m) =>
          m.statut === "programme" &&
          ((m.equipe_domicile_id === kadutu.id && m.equipe_exterieur_id === ibanda.id) ||
            (m.equipe_domicile_id === ibanda.id && m.equipe_exterieur_id === kadutu.id)),
      );
      if (deja) {
        nav(`/orga/matchs/${deja.id}`);
        return;
      }
      const m = await api.creerMatch({
        saison_id: saison.id,
        journee: "TEST",
        date_heure: new Date().toISOString(),
        stade: kadutu.stade || "Stade Kadutu",
        equipe_domicile_id: kadutu.id,
        equipe_exterieur_id: ibanda.id,
      });
      nav(`/orga/matchs/${m.id}`);
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function actFile(fn, ok) {
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      await fn();
      setMsg(ok);
      setRejetId(null);
      setRejetCom("");
      await load();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    clearTokens();
    nav("/", { replace: true });
  }

  return (
    <div className="shell">
      <p className="kicker" style={{ paddingTop: "1rem" }}>
        {me?.nom_complet || me?.email} ·{" "}
        <button className="linkish" type="button" onClick={logout}>Déconnexion</button>
      </p>
      <section className="hero">
        <h1>Organisateur</h1>
        <p className="lead">Démarrer, saisir, terminer, valider. Rien n’est officiel avant validation.</p>
      </section>
      {err && <p className="erreur">{err}</p>}
      {msg && <p className="empty">{msg}</p>}

      <div className="section-head">
        <h2>Nouvelle compétition</h2>
      </div>
      <p className="lead">Pas une DEMO. Le nom n’est pas figé dans le produit.</p>
      <form className="compte-form" onSubmit={creerCompetitionTerrain}>
        <label className="field">
          Nom
          <input value={nomComp} onChange={(e) => setNomComp(e.target.value)} required />
        </label>
        <label className="field">
          Type
          <select value={typeComp} onChange={(e) => setTypeComp(e.target.value)}>
            <option value="tournoi">Tournoi</option>
            <option value="championnat">Championnat</option>
            <option value="coupe">Coupe</option>
          </select>
        </label>
        <label className="field">
          Saison / édition
          <input value={nomSaison} onChange={(e) => setNomSaison(e.target.value)} placeholder="ex. 2e semestre 2026" />
        </label>
        <label className="field">
          Date de début
          <input type="date" value={dateDebut} onChange={(e) => setDateDebut(e.target.value)} />
        </label>
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "…" : "Créer la compétition"}
        </button>
      </form>

      {saison && (
        <>
          <div className="section-head">
            <h2>Équipes ({equipes.length})</h2>
          </div>
          <p className="lead">Nom = identité. Ville = département. Une ville peut avoir plusieurs équipes.</p>
          {equipes.length === 0 && <p className="empty">Aucune équipe inscrite.</p>}
          {equipes.length > 0 && (
            <div className="sheet">
              {equipes.map((c) => (
                <div key={c.id} className="club-tile">
                  <strong>{stripDemo(c.nom)}</strong>
                  <span className="meta">{[c.ville, c.stade].filter(Boolean).join(" — ")}</span>
                </div>
              ))}
            </div>
          )}
          <form className="compte-form" onSubmit={creerEquipe}>
            <label className="field">
              Nom de l’équipe
              <input value={nomEquipe} onChange={(e) => setNomEquipe(e.target.value)} required />
            </label>
            <label className="field">
              Ville / département
              <input value={villeEquipe} onChange={(e) => setVilleEquipe(e.target.value)} required />
            </label>
            <label className="field">
              Stade
              <input value={stadeEquipe} onChange={(e) => setStadeEquipe(e.target.value)} />
            </label>
            <button className="btn btn-primary" type="submit" disabled={busy}>
              {busy ? "…" : "Inscrire l’équipe"}
            </button>
          </form>

          <div className="section-head">
            <h2>Programmer un match</h2>
          </div>
          {equipes.length < 2 ? (
            <p className="empty">Inscrivez au moins deux équipes avant de programmer.</p>
          ) : (
            <form className="compte-form" onSubmit={programmerMatch}>
              <label className="field">
                Domicile
                <select value={domId} onChange={(e) => setDomId(e.target.value)} required>
                  <option value="">—</option>
                  {equipes.map((c) => (
                    <option key={c.id} value={c.id}>{stripDemo(c.nom)}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                Extérieur
                <select value={extId} onChange={(e) => setExtId(e.target.value)} required>
                  <option value="">—</option>
                  {equipes.map((c) => (
                    <option key={c.id} value={c.id}>{stripDemo(c.nom)}</option>
                  ))}
                </select>
              </label>
              <div className="comp-grid">
                <label className="field">
                  Date
                  <input type="date" value={dateMatch} onChange={(e) => setDateMatch(e.target.value)} required />
                </label>
                <label className="field">
                  Heure
                  <input type="time" value={heureMatch} onChange={(e) => setHeureMatch(e.target.value)} required />
                </label>
              </div>
              <label className="field">
                Stade
                <input
                  value={stadeMatch}
                  onChange={(e) => setStadeMatch(e.target.value)}
                  placeholder={equipes.find((c) => String(c.id) === String(domId))?.stade || ""}
                />
              </label>
              <label className="field">
                Journée
                <input
                  value={journee}
                  onChange={(e) => setJournee(e.target.value)}
                  maxLength={20}
                  placeholder="ex. J1"
                />
              </label>
              <button className="btn btn-primary" type="submit" disabled={busy}>
                {busy ? "…" : "Programmer le match"}
              </button>
            </form>
          )}
        </>
      )}

      {competition?.est_demo && (
        <p>
          <button className="btn" type="button" disabled={busy} onClick={preparerTest}>
            {busy ? "…" : "Match test · Kadutu — Ibanda"}
          </button>
        </p>
      )}

      <div className="section-head">
        <h2>File d’événements ({file.length})</h2>
      </div>
      {file.length === 0 && <p className="empty">Rien en attente.</p>}
      <ul className="timeline">
        {file.map((e) => (
          <li key={e.id}>
            <div>
              Match #{e.match_id} · {formatMinute(e.minute, e.minute_additionnelle)} · {e.type}
              {" · "}
              <Link to={`/orga/matchs/${e.match_id}`}>Ouvrir</Link>
            </div>
            <div className="file-actions">
              <button
                className="btn"
                type="button"
                disabled={busy}
                onClick={() => actFile(() => api.validerEvenement(e.id), "Événement validé.")}
              >
                Valider
              </button>
              {rejetId === e.id ? (
                <>
                  <input
                    className="field-inline"
                    value={rejetCom}
                    onChange={(ev) => setRejetCom(ev.target.value)}
                    placeholder="Motif du rejet"
                  />
                  <button
                    className="btn btn-danger"
                    type="button"
                    disabled={busy || !rejetCom.trim()}
                    onClick={() => actFile(() => api.rejeterEvenement(e.id, rejetCom.trim()), "Événement rejeté.")}
                  >
                    Confirmer
                  </button>
                </>
              ) : (
                <button className="btn btn-danger" type="button" disabled={busy} onClick={() => { setRejetId(e.id); setRejetCom(""); }}>
                  Rejeter
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>

      <div className="section-head">
        <h2>Matchs</h2>
      </div>
      <div className="sheet">
        {matchs.map((m) => (
          <Link key={m.id} to={`/orga/matchs/${m.id}`} className="scoreboard">
            <div className="sb-line">
              <span className="sb-name">{nom(m.equipe_domicile_id)}</span>
              <span className="sb-score">
                {m.score_domicile}<span className="sb-dash">–</span>{m.score_exterieur}
              </span>
              <span className="sb-name away">{nom(m.equipe_exterieur_id)}</span>
            </div>
            <div className="sb-meta">
              <span className="sb-meta-journee">{STATUT[m.statut] || m.statut}</span>
              <span className="sb-meta-lieu">{[m.journee, fmtQuand(m.date_heure)].filter(Boolean).join(" · ")}</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
