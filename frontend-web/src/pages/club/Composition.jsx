import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api.js";
import { useKivu } from "../../context.jsx";
import { labelPoste, stripDemo } from "../../display.js";
import { fmtQuand, STATUT_MATCH } from "../orga/saison.js";

const FORMATIONS = [
  "4-2-3-1", "4-3-3", "4-4-2", "4-1-4-1", "4-4-1-1", "4-3-2-1", "4-5-1",
  "4-2-2-2", "3-5-2", "3-4-3", "3-4-2-1", "3-4-1-2", "3-6-1", "3-3-3-1",
  "5-3-2", "5-4-1", "5-2-3", "5-3-1-1", "4-1-2-1-2", "4-2-1-3", "4-3-1-2", "3-2-4-1",
];
const POSTES = [
  { id: "tous", label: "Tous" },
  { id: "gardien", label: "Gardiens" },
  { id: "defenseur", label: "Défenseurs" },
  { id: "milieu", label: "Milieux" },
  { id: "attaquant", label: "Attaquants" },
];

function lignesPourFormation(value) {
  const nombres = String(value || "")
    .split("-")
    .map((n) => Number(n))
    .filter((n) => Number.isInteger(n) && n > 0);
  if (nombres.length < 2) return lignesPourFormation("4-3-3");
  return [
    { label: "Gardien", poste: "gardien", places: 1 },
    ...nombres.map((places, index) => ({
      label: index === 0 ? "Défense" : index === nombres.length - 1 ? "Attaque" : "Milieu",
      poste: index === 0 ? "defenseur" : index === nombres.length - 1 ? "attaquant" : "milieu",
      places,
    })),
  ];
}

function nomCourt(nom) {
  const mots = String(nom || "Joueur").trim().split(/\s+/).filter(Boolean);
  if (mots.length <= 2) return mots.join(" ") || "Joueur";
  // Garder deux mots rend les noms DEMO lisibles (Joueur 1) et
  // conserve généralement prénom + nom pour un joueur réel.
  return mots.slice(-2).join(" ");
}

function initials(nom) {
  const mots = String(nom || "?").trim().split(/\s+/).filter(Boolean);
  return mots.slice(0, 2).map((mot) => mot.charAt(0)).join("").toUpperCase() || "?";
}

function valeurStatut(eligibilite) {
  return eligibilite?.statut || "";
}

export default function Composition() {
  const { matchId } = useParams();
  const { clubsById } = useKivu();
  const [moi, setMoi] = useState(null);
  const [match, setMatch] = useState(null);
  const [compo, setCompo] = useState(null);
  const [joueurs, setJoueurs] = useState([]);
  const [staff, setStaff] = useState([]);
  const [choix, setChoix] = useState({});
  const [formation, setFormation] = useState("");
  const [staffId, setStaffId] = useState("");
  const [numeros, setNumeros] = useState({});
  const [eligibilites, setEligibilites] = useState({});
  const [chargement, setChargement] = useState(true);
  const [erreurChargement, setErreurChargement] = useState("");
  const [avertissements, setAvertissements] = useState([]);
  const [recherche, setRecherche] = useState("");
  const [filtrePoste, setFiltrePoste] = useState("tous");
  const [uniquementSelectionnes, setUniquementSelectionnes] = useState(false);
  const [message, setMessage] = useState("");
  const [erreur, setErreur] = useState("");
  const [sauvegardeEnCours, setSauvegardeEnCours] = useState(false);
  const [modifie, setModifie] = useState(false);
  const [tentative, setTentative] = useState(0);

  const clubId = moi?.club_id ?? null;
  const equipe = match
    ? match.equipe_domicile_id === clubId
      ? "domicile"
      : match.equipe_exterieur_id === clubId
        ? "exterieur"
        : null
    : null;
  const verrouille = Boolean(
    match?.locked || ["en_cours", "termine", "valide"].includes(match?.statut),
  );

  useEffect(() => {
    let actif = true;

    async function charger() {
      setChargement(true);
      setErreurChargement("");
      setErreur("");
      setMessage("");
      setAvertissements([]);
      try {
        const premiers = await Promise.allSettled([
          api.me(),
          api.match(matchId),
          api.composition(matchId),
        ]);
        if (!actif) return;
        const [moiResultat, matchResultat, compoResultat] = premiers;
        if (moiResultat.status === "rejected") throw new Error("Session club indisponible. Reconnectez-vous puis réessayez.");
        if (matchResultat.status === "rejected") throw new Error(matchResultat.reason?.message || "Match introuvable ou indisponible.");
        if (compoResultat.status === "rejected") throw new Error(compoResultat.reason?.message || "Composition indisponible pour ce match.");

        const compte = moiResultat.value;
        const matchCharge = matchResultat.value;
        const composition = compoResultat.value;
        const club = compte?.club_id;
        const cote = club
          ? matchCharge.equipe_domicile_id === club
            ? "domicile"
            : matchCharge.equipe_exterieur_id === club
              ? "exterieur"
              : null
          : null;
        if (!club) throw new Error("Votre compte n'est rattaché à aucun club.");
        if (!cote) throw new Error("Ce match ne concerne pas votre club.");

        const ressources = await Promise.allSettled([
          api.joueurs(club),
          api.staffClub(club),
          api.eligibiliteMatch(matchId, club),
        ]);
        if (!actif) return;

        const avertissementsRessources = [];
        const joueursResultat = ressources[0];
        const staffResultat = ressources[1];
        const eligibilitesResultat = ressources[2];
        const effectifCharge = joueursResultat.status === "fulfilled" ? (joueursResultat.value || []) : [];
        const encadrement = staffResultat.status === "fulfilled" ? (staffResultat.value || []) : [];
        const eligibilityRows = eligibilitesResultat.status === "fulfilled" ? (eligibilitesResultat.value || []) : [];
        if (joueursResultat.status === "rejected") avertissementsRessources.push("L'effectif n'a pas pu être chargé. Réessayez avant de sauvegarder.");
        if (staffResultat.status === "rejected") avertissementsRessources.push("Le staff n'a pas pu être chargé. L'entraîneur ne peut pas être modifié pour le moment.");
        if (eligibilitesResultat.status === "rejected") avertissementsRessources.push("Le contrôle d'éligibilité est momentanément indisponible. Le serveur effectuera tout de même une vérification lors de l'enregistrement.");

        const bloc = composition?.[cote] || {};
        const choixInitial = {};
        const numerosInitiaux = {};
        (bloc.titulaires || []).forEach((joueur) => {
          choixInitial[joueur.id] = "titulaire";
          if (joueur.numero != null) numerosInitiaux[joueur.id] = String(joueur.numero);
        });
        (bloc.banc || []).forEach((joueur) => {
          choixInitial[joueur.id] = "remplacant";
          if (joueur.numero != null) numerosInitiaux[joueur.id] = String(joueur.numero);
        });

        const joueursParId = new Map(effectifCharge.map((joueur) => [joueur.id, joueur]));
        const joueursDejaDansComposition = [...(bloc.titulaires || []), ...(bloc.banc || [])];
        const joueursAbsentsDeLEffectif = joueursDejaDansComposition.filter((joueur) => !joueursParId.has(joueur.id));
        joueursAbsentsDeLEffectif.forEach((joueur) => {
          joueursParId.set(joueur.id, { ...joueur, compositionSeulement: true });
        });
        const effectif = [...joueursParId.values()];
        if (joueursAbsentsDeLEffectif.length) {
          avertissementsRessources.push(
            `${joueursAbsentsDeLEffectif.length} joueur(s) de la feuille ne figurent plus dans l'effectif actuellement chargé. Vérifiez avant d'enregistrer.`,
          );
        }

        setMoi(compte);
        setMatch(matchCharge);
        setCompo(composition);
        setJoueurs(effectif);
        setStaff(encadrement);
        setEligibilites(Object.fromEntries(eligibilityRows.map((row) => [row.joueur_id, row])));
        setChoix(choixInitial);
        setNumeros(numerosInitiaux);
        setFormation(bloc.formation || "");
        setStaffId(bloc.staff ? String(bloc.staff.id) : "");
        setAvertissements(avertissementsRessources);
        setModifie(false);
      } catch (e) {
        if (actif) setErreurChargement(e?.message || "Impossible de charger la composition.");
      } finally {
        if (actif) setChargement(false);
      }
    }

    charger();
    return () => {
      actif = false;
    };
  }, [matchId, tentative]);

  useEffect(() => {
    if (!modifie) return undefined;
    const prevenirQuitte = (event) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", prevenirQuitte);
    return () => window.removeEventListener("beforeunload", prevenirQuitte);
  }, [modifie]);

  const comptes = useMemo(() => {
    const vals = Object.values(choix);
    return {
      titulaires: vals.filter((v) => v === "titulaire").length,
      banc: vals.filter((v) => v === "remplacant").length,
    };
  }, [choix]);

  const maxBanc = compo?.max_remplacants ?? 7;

  const validation = useMemo(() => {
    const erreurs = [];
    const avertissementsValidation = [];
    if (comptes.titulaires !== 11) {
      erreurs.push(`La composition doit contenir exactement 11 titulaires (actuellement ${comptes.titulaires}).`);
    }
    if (comptes.banc > maxBanc) erreurs.push(`La composition dépasse la limite de ${maxBanc} remplaçants.`);

    const numerosVus = new Map();
    joueurs.forEach((joueur) => {
      if (!choix[joueur.id]) return;
      const valeur = numeros[joueur.id] ?? (joueur.numero != null ? String(joueur.numero) : "");
      if (valeur === "") return;
      const numero = Number(valeur);
      if (!Number.isInteger(numero) || numero < 1 || numero > 99) {
        erreurs.push(`${joueur.nom_complet} doit avoir un numéro entre 1 et 99.`);
        return;
      }
      if (numerosVus.has(numero)) {
        erreurs.push(`Le numéro ${numero} est attribué à ${numerosVus.get(numero)} et ${joueur.nom_complet}.`);
      } else {
        numerosVus.set(numero, joueur.nom_complet);
      }
    });

    joueurs.forEach((joueur) => {
      if (choix[joueur.id] && joueur.compositionSeulement) {
        erreurs.push(`${joueur.nom_complet} n'est plus présent dans l'effectif actuel. Retirez-le ou vérifiez son rattachement avant d'enregistrer.`);
      }
      if (choix[joueur.id] && valeurStatut(eligibilites[joueur.id]) === "BLOQUANT") {
        erreurs.push(`${joueur.nom_complet} ne peut pas être sélectionné : ${eligibilites[joueur.id]?.message || "joueur inéligible"}`);
      }
    });
    if (!formation.trim()) {
      avertissementsValidation.push("La formation n'est pas encore renseignée.");
    } else if (!/^\d+(?:-\d+)+$/.test(formation.trim().replace(/[–—]/g, "-"))) {
      erreurs.push("La formation doit utiliser un format comme 4-3-3.");
    }
    return { erreurs: [...new Set(erreurs)], avertissements: avertissementsValidation };
  }, [choix, comptes, eligibilites, formation, joueurs, maxBanc, numeros]);

  const joueursFiltres = useMemo(() => {
    const texte = recherche.trim().toLocaleLowerCase("fr");
    return [...joueurs]
      .filter((joueur) => {
        const correspondNom = !texte || String(joueur.nom_complet || "").toLocaleLowerCase("fr").includes(texte);
        const correspondPoste = filtrePoste === "tous" || joueur.poste === filtrePoste;
        const correspondSelection = !uniquementSelectionnes || Boolean(choix[joueur.id]);
        return correspondNom && correspondPoste && correspondSelection;
      })
      .sort((a, b) => {
        const aSelectionne = choix[a.id] ? 0 : 1;
        const bSelectionne = choix[b.id] ? 0 : 1;
        return aSelectionne - bSelectionne || String(a.nom_complet || "").localeCompare(String(b.nom_complet || ""), "fr");
      });
  }, [choix, filtrePoste, joueurs, uniquementSelectionnes, recherche]);

  const titulaires = useMemo(
    () => joueurs.filter((joueur) => choix[joueur.id] === "titulaire"),
    [choix, joueurs],
  );
  const banc = useMemo(
    () => joueurs.filter((joueur) => choix[joueur.id] === "remplacant"),
    [choix, joueurs],
  );

  const nomEquipe = (id, secours) => stripDemo(clubsById?.[id]?.nom) || secours;
  const nomDomicile = nomEquipe(match?.equipe_domicile_id, "Équipe domicile");
  const nomExterieur = nomEquipe(match?.equipe_exterieur_id, "Équipe extérieure");
  const monNom = equipe === "domicile" ? nomDomicile : nomExterieur;
  const adversaireNom = equipe === "domicile" ? nomExterieur : nomDomicile;
  const monClub = clubsById?.[clubId];
  const adversaireClub = clubsById?.[equipe === "domicile" ? match?.equipe_exterieur_id : match?.equipe_domicile_id];

  function marquerModifie() {
    setModifie(true);
    setMessage("");
    setErreur("");
  }

  function choisirRole(joueur, role) {
    if (verrouille) return;
    const actuel = choix[joueur.id];
    const eligibilite = eligibilites[joueur.id];
    if (actuel === role) {
      setChoix((ancien) => ({ ...ancien, [joueur.id]: undefined }));
      marquerModifie();
      return;
    }
    if (joueur.compositionSeulement) {
      setErreur("Ce joueur est encore affiché pour protéger la feuille existante, mais il ne figure plus dans l'effectif actuel. Retirez-le avant de sauvegarder.");
      return;
    }
    if (eligibilite?.statut === "BLOQUANT") {
      setErreur(eligibilite.message || "Ce joueur ne peut pas être sélectionné.");
      return;
    }
    if (role === "titulaire" && comptes.titulaires >= 11) {
      setErreur("Les 11 places de titulaires sont déjà occupées.");
      return;
    }
    if (role === "remplacant" && comptes.banc >= maxBanc) {
      setErreur(`Les ${maxBanc} places du banc sont déjà occupées.`);
      return;
    }
    setChoix((ancien) => ({ ...ancien, [joueur.id]: role }));
    marquerModifie();
  }

  function modifierNumero(joueurId, value) {
    if (verrouille) return;
    setNumeros((ancien) => ({ ...ancien, [joueurId]: value }));
    marquerModifie();
  }

  function joueurPourSlot(joueursDePoste, index) {
    return joueursDePoste[index] || null;
  }

  function pitchRows() {
    const lignes = lignesPourFormation(formation);
    const restants = Object.fromEntries(["gardien", "defenseur", "milieu", "attaquant"].map((poste) => [
      poste,
      titulaires.filter((joueur) => joueur.poste === poste),
    ]));
    const utilises = new Set();
    return lignes.map((ligne) => {
      const joueursDeLigne = [];
      while (joueursDeLigne.length < ligne.places) {
        const preferes = (restants[ligne.poste] || []).filter((joueur) => !utilises.has(joueur.id));
        // Priorité au poste enregistré ; le fallback final garantit que
        // les onze titulaires restent visibles, même si un poste manque
        // dans les choix du coach.
        const candidat = preferes[0]
          || titulaires.find((joueur) => !utilises.has(joueur.id));
        if (!candidat) break;
        utilises.add(candidat.id);
        joueursDeLigne.push(candidat);
      }
      return { ...ligne, joueurs: joueursDeLigne };
    });
  }

  async function enregistrer() {
    setMessage("");
    setErreur("");
    if (verrouille) {
      setErreur("Match verrouillé : la composition ne peut plus être modifiée.");
      return;
    }
    if (validation.erreurs.length) {
      setErreur(validation.erreurs[0]);
      return;
    }
    if (!equipe) {
      setErreur("Équipe non déterminée pour ce match.");
      return;
    }
    setSauvegardeEnCours(true);
    try {
      const lignes = joueurs
        .filter((joueur) => choix[joueur.id])
        .map((joueur) => {
          const valeurNumero = numeros[joueur.id] ?? (joueur.numero != null ? String(joueur.numero) : "");
          return {
            joueur_id: joueur.id,
            statut: choix[joueur.id],
            numero: valeurNumero === "" ? null : Number(valeurNumero),
          };
        });
      const nouvelleComposition = await api.enregistrerComposition(matchId, {
        equipe,
        formation: formation.trim() || null,
        staff_id: staffId ? Number(staffId) : null,
        joueurs: lignes,
      });
      const bloc = nouvelleComposition?.[equipe] || {};
      const choixServeur = {};
      const numerosServeur = {};
      (bloc.titulaires || []).forEach((joueur) => {
        choixServeur[joueur.id] = "titulaire";
        if (joueur.numero != null) numerosServeur[joueur.id] = String(joueur.numero);
      });
      (bloc.banc || []).forEach((joueur) => {
        choixServeur[joueur.id] = "remplacant";
        if (joueur.numero != null) numerosServeur[joueur.id] = String(joueur.numero);
      });
      setCompo(nouvelleComposition);
      setChoix(choixServeur);
      setNumeros(numerosServeur);
      setFormation(bloc.formation || "");
      setStaffId(bloc.staff ? String(bloc.staff.id) : "");
      setModifie(false);
      setMessage("Composition enregistrée avec succès.");
    } catch (e) {
      setErreur(e?.message || "Enregistrement refusé par le serveur.");
    } finally {
      setSauvegardeEnCours(false);
    }
  }

  if (chargement) {
    return (
      <section className="hero composition-page">
        <p className="kicker">Feuille de composition</p>
        <h1>Préparation du match</h1>
        <div className="composition-loading" aria-live="polite">
          <span className="composition-loading-dot" />
          <span>Chargement du match, de l’effectif et des contrôles…</span>
        </div>
      </section>
    );
  }

  if (erreurChargement) {
    return (
      <section className="hero composition-page">
        <p className="kicker"><Link to={`/matchs/${matchId}`}>← Retour au match</Link></p>
        <h1>Composition indisponible</h1>
        <div className="composition-alert composition-alert-error" role="alert">
          <strong>Nous n’avons pas pu charger cette feuille.</strong>
          <span>{erreurChargement}</span>
        </div>
        <button type="button" className="btn btn-primary composition-retry" onClick={() => setTentative((n) => n + 1)}>
          Réessayer
        </button>
      </section>
    );
  }

  if (!moi || !match || !equipe) {
    return <p className="empty">Ce match ne concerne pas votre club.</p>;
  }

  const lignesTerrain = pitchRows();
  const joueursPlaces = new Set(lignesTerrain.flatMap((ligne) => ligne.joueurs.map((joueur) => joueur.id)));
  const titulairesNonPlaces = titulaires.filter((joueur) => !joueursPlaces.has(joueur.id));
  const pourcentageTitulaires = Math.min(100, Math.round((comptes.titulaires / 11) * 100));
  const pourcentageBanc = Math.min(100, Math.round((comptes.banc / Math.max(maxBanc, 1)) * 100));

  return (
    <section className="hero composition-page">
      <p className="kicker composition-back"><Link to={`/matchs/${matchId}`}>← Retour au match</Link></p>
      <p className="kicker">Feuille de composition · {monNom}</p>
      <h1>{monNom}</h1>
      <p className="lead">Préparez la feuille de votre équipe. Les contrôles officiels restent appliqués par le serveur.</p>

      <section className="composition-match-card" aria-label="Contexte du match">
        <div className="composition-match-team composition-match-team-home">
          <span className="composition-crest">
            {monClub?.logo_url ? <img src={monClub.logo_url} alt="" /> : initials(monNom)}
          </span>
          <strong>{nomDomicile}</strong>
          <small>Domicile</small>
        </div>
        <div className="composition-match-middle">
          <span className="composition-match-vs">VS</span>
          <span>{fmtQuand(match.date_heure) || "Date à confirmer"}</span>
          {match.stade && <span>{match.stade}</span>}
          <span className={`composition-status ${verrouille ? "is-locked" : ""}`}>
            {STATUT_MATCH[match.statut] || match.statut}
          </span>
        </div>
        <div className="composition-match-team composition-match-team-away">
          <span className="composition-crest">
            {adversaireClub?.logo_url ? <img src={adversaireClub.logo_url} alt="" /> : initials(adversaireNom)}
          </span>
          <strong>{nomExterieur}</strong>
          <small>Extérieur</small>
        </div>
      </section>

      <section className="composition-summary" aria-label="Résumé de la composition">
        <div className="composition-summary-head">
          <div>
            <p className="composition-eyebrow">État de la feuille</p>
            <strong>{verrouille ? "Composition verrouillée" : modifie ? "Modifications non enregistrées" : "Brouillon enregistré"}</strong>
          </div>
          <span className={`composition-draft-badge ${verrouille ? "is-locked" : modifie ? "is-dirty" : "is-saved"}`}>
            {verrouille ? "Verrouillée" : modifie ? "À enregistrer" : "Brouillon"}
          </span>
        </div>
        <div className="composition-counters">
          <div className="composition-counter">
            <div><span>Onze titulaire</span><strong>{comptes.titulaires}/11</strong></div>
            <div className="composition-progress"><span style={{ width: `${pourcentageTitulaires}%` }} /></div>
          </div>
          <div className="composition-counter">
            <div><span>Banc</span><strong>{comptes.banc}/{maxBanc}</strong></div>
            <div className="composition-progress composition-progress-bench"><span style={{ width: `${pourcentageBanc}%` }} /></div>
          </div>
        </div>
      </section>

      {verrouille && (
        <div className="composition-alert composition-alert-warning" role="status">
          <strong>Ce match est verrouillé.</strong>
          <span>La feuille reste consultable, mais aucune modification n’est autorisée.</span>
        </div>
      )}
      {avertissements.map((avertissement) => (
        <div key={avertissement} className="composition-alert composition-alert-warning" role="status">
          <span>{avertissement}</span>
        </div>
      ))}
      {validation.avertissements.map((avertissement) => (
        <div key={avertissement} className="composition-alert composition-alert-info" role="status">
          <span>{avertissement}</span>
        </div>
      ))}
      {message && <p className="composition-feedback composition-feedback-ok" role="status">{message}</p>}
      {erreur && <p className="composition-feedback composition-feedback-error" role="alert">{erreur}</p>}

      <section className="composition-selected-summary" aria-label="Joueurs sélectionnés">
        <div className="composition-section-heading">
          <div><p className="composition-eyebrow">Feuille automatique</p><h2>Noms sélectionnés</h2></div>
          <span className="composition-section-count">Mis à jour depuis l’effectif</span>
        </div>
        <div className="composition-selected-grid">
          <div className="composition-selected-column">
            <div className="composition-selected-title"><strong>Titulaires</strong><span>{titulaires.length}/11</span></div>
            {titulaires.length ? (
              <ol className="composition-selected-list">
                {titulaires.map((joueur) => (
                  <li key={joueur.id}><span className="composition-selected-number">{numeros[joueur.id] || joueur.numero || "—"}</span><span><strong>{joueur.nom_complet}</strong><small>{labelPoste(joueur.poste) || "Poste non renseigné"}</small></span></li>
                ))}
              </ol>
            ) : <p className="composition-selected-empty">Les noms apparaîtront automatiquement ici.</p>}
          </div>
          <div className="composition-selected-column">
            <div className="composition-selected-title"><strong>Banc</strong><span>{banc.length}/{maxBanc}</span></div>
            {banc.length ? (
              <ol className="composition-selected-list">
                {banc.map((joueur) => (
                  <li key={joueur.id}><span className="composition-selected-number">{numeros[joueur.id] || joueur.numero || "—"}</span><span><strong>{joueur.nom_complet}</strong><small>{labelPoste(joueur.poste) || "Poste non renseigné"}</small></span></li>
                ))}
              </ol>
            ) : <p className="composition-selected-empty">Les noms du banc apparaîtront automatiquement ici.</p>}
          </div>
        </div>
      </section>

      <section className="composition-settings" aria-label="Réglages de la composition">
        <div className="composition-section-heading">
          <div><p className="composition-eyebrow">Paramètres</p><h2>Formation et encadrement</h2></div>
        </div>
        <div className="composition-settings-grid">
          <label className="composition-field">
            <span>Formation tactique</span>
            <select
              value={formation}
              onChange={(event) => { setFormation(event.target.value); marquerModifie(); }}
              disabled={verrouille}
              aria-describedby="formation-help"
            >
              <option value="">— Choisir une formation —</option>
              {FORMATIONS.map((modele) => <option key={modele} value={modele}>{modele}</option>)}
              {formation && !FORMATIONS.includes(formation) && <option value={formation}>{formation} · ancienne valeur</option>}
            </select>
            <small id="formation-help">Les joueurs sont répartis automatiquement sur les lignes de la formation.</small>
          </label>
          <label className="composition-field">
            <span>Entraîneur</span>
            <select value={staffId} onChange={(event) => { setStaffId(event.target.value); marquerModifie(); }} disabled={verrouille || !staff.length}>
              <option value="">— À compléter —</option>
              {staff.map((membre) => (
                <option key={membre.id} value={membre.id}>{membre.nom_complet || membre.full_name}{membre.role ? ` · ${membre.role}` : ""}</option>
              ))}
            </select>
            {!staff.length && <small>Aucun entraîneur disponible dans le staff enregistré.</small>}
          </label>
        </div>
        <div className="composition-formation-chips" aria-label="Formations proposées">
          {FORMATIONS.map((modele) => (
            <button key={modele} type="button" className={formation === modele ? "is-active" : ""} onClick={() => { setFormation(modele); marquerModifie(); }} disabled={verrouille}>
              {modele}
            </button>
          ))}
        </div>
      </section>

      <section className="composition-pitch-section" aria-label="Aperçu de l'équipe titulaire">
        <div className="composition-section-heading">
          <div><p className="composition-eyebrow">Aperçu</p><h2>Onze titulaire</h2></div>
          <span className="composition-section-count">{formation || "Formation à compléter"}</span>
        </div>
        <p className="composition-help">Aperçu organisé selon le poste enregistré du joueur. Il ne remplace pas le contrôle officiel de la feuille.</p>
        <div className="composition-pitch">
          <div className="composition-pitch-center-line" />
          <div className="composition-pitch-circle" />
          <div className="composition-pitch-rows">
            {lignesTerrain.map((ligne) => (
              <div className="composition-pitch-row" key={`${ligne.label}-${ligne.poste}`}>
                {Array.from({ length: ligne.places }).map((_, index) => {
                  const joueur = joueurPourSlot(ligne.joueurs, index);
                  return joueur ? (
                    <span className="composition-pitch-player" key={joueur.id} title={`${joueur.nom_complet} · ${labelPoste(joueur.poste)}`}>
                      <b>{numeros[joueur.id] || joueur.numero || "—"}</b>
                      <small>{nomCourt(joueur.nom_complet)}</small>
                    </span>
                  ) : (
                    <span className="composition-pitch-empty" key={`${ligne.label}-vide-${index}`} aria-label={`${ligne.label} à compléter`}>+</span>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
        {titulairesNonPlaces.length > 0 && (
          <p className="composition-unplaced">Joueurs titulaires non placés dans l’aperçu : {titulairesNonPlaces.map((joueur) => joueur.nom_complet).join(", ")}</p>
        )}
      </section>

      <section className="composition-roster" aria-label="Effectif disponible">
        <div className="composition-section-heading">
          <div><p className="composition-eyebrow">Sélection</p><h2>Effectif disponible</h2></div>
          <span className="composition-section-count">{joueursFiltres.length}/{joueurs.length}</span>
        </div>
        <div className="composition-roster-tools">
          <label className="composition-search">
            <span className="sr-only">Rechercher un joueur</span>
            <input value={recherche} onChange={(event) => setRecherche(event.target.value)} placeholder="Rechercher un joueur" />
          </label>
          <label className="composition-only-selected">
            <input type="checkbox" checked={uniquementSelectionnes} onChange={(event) => setUniquementSelectionnes(event.target.checked)} />
            <span>Sélectionnés seulement</span>
          </label>
        </div>
        <div className="composition-poste-filters" role="tablist" aria-label="Filtrer par poste">
          {POSTES.map((poste) => (
            <button key={poste.id} type="button" role="tab" aria-selected={filtrePoste === poste.id} className={filtrePoste === poste.id ? "is-active" : ""} onClick={() => setFiltrePoste(poste.id)}>
              {poste.label}
            </button>
          ))}
        </div>
        {joueurs.length === 0 ? (
          <div className="composition-empty-state">Aucun joueur enregistré pour ce club. Vérifiez l’effectif avant la rencontre.</div>
        ) : joueursFiltres.length === 0 ? (
          <div className="composition-empty-state">Aucun joueur ne correspond à cette recherche ou à ce filtre.</div>
        ) : (
          <div className="composition-player-list">
            {joueursFiltres.map((joueur) => {
              const role = choix[joueur.id];
              const eligibilite = eligibilites[joueur.id];
              const bloquant = eligibilite?.statut === "BLOQUANT";
              const numero = numeros[joueur.id] ?? (joueur.numero != null ? String(joueur.numero) : "");
              return (
                <article key={joueur.id} className={`composition-player-card ${role ? `is-${role}` : ""} ${bloquant || joueur.compositionSeulement ? "is-blocked" : ""}`}>
                  <span className="composition-player-avatar">
                    {joueur.photo_url ? <img src={joueur.photo_url} alt="" /> : initials(joueur.nom_complet)}
                  </span>
                  <div className="composition-player-info">
                    <strong>{joueur.nom_complet}</strong>
                    <span>{labelPoste(joueur.poste) || "Poste non renseigné"}{joueur.numero != null ? ` · N° profil ${joueur.numero}` : ""}</span>
                    {eligibilite && <small className={bloquant ? "is-blocked-text" : eligibilite.statut === "ATTENTION" ? "is-attention-text" : "is-ok-text"}>{eligibilite.message}</small>}
                    {joueur.compositionSeulement && <small className="is-blocked-text">Absent de l’effectif actuel · à vérifier</small>}
                  </div>
                  <label className="composition-number-field">
                    <span>N°</span>
                    <input type="number" min="1" max="99" inputMode="numeric" value={numero} onChange={(event) => modifierNumero(joueur.id, event.target.value)} disabled={verrouille} aria-label={`Numéro de ${joueur.nom_complet}`} />
                  </label>
                  <div className="composition-player-actions">
                    <button type="button" className={role === "titulaire" ? "is-active" : ""} onClick={() => choisirRole(joueur, "titulaire")} disabled={verrouille || (bloquant && !role)}>
                      Titulaire
                    </button>
                    <button type="button" className={role === "remplacant" ? "is-active" : ""} onClick={() => choisirRole(joueur, "remplacant")} disabled={verrouille || (bloquant && !role)}>
                      Banc
                    </button>
                    {role && <button type="button" className="is-remove" onClick={() => choisirRole(joueur, role)} disabled={verrouille}>Retirer</button>}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <div className="composition-save-bar">
        <div>
          <strong>{verrouille ? "Feuille verrouillée" : modifie ? "Des modifications restent à enregistrer" : "Feuille à jour"}</strong>
          {!verrouille && validation.erreurs.length > 0 && <small>{validation.erreurs.length} contrôle(s) à corriger avant sauvegarde.</small>}
        </div>
        <button type="button" className="btn btn-primary" onClick={enregistrer} disabled={verrouille || sauvegardeEnCours || validation.erreurs.length > 0}>
          {sauvegardeEnCours ? "Enregistrement…" : verrouille ? "Match verrouillé" : "Enregistrer le brouillon"}
        </button>
      </div>
    </section>
  );
}
