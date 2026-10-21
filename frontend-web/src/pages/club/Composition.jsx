import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api.js";
import { useKivu } from "../../context.jsx";
import { labelPoste, stripDemo } from "../../display.js";
import { fmtQuand, STATUT_MATCH } from "../orga/saison.js";
import {
  FORMATIONS,
  clePosition,
  libellePosition,
  lignesAvecPlacements,
  lireClePosition,
  placementDuJoueur,
  slotValide,
  slotsPourFormation,
} from "../../compositionPositions.js";

const POSTES = [
  { id: "tous", label: "Tous" },
  { id: "gardien", label: "Gardiens" },
  { id: "defenseur", label: "Défenseurs" },
  { id: "milieu", label: "Milieux" },
  { id: "attaquant", label: "Attaquants" },
];

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

function normaliserFormation(value) {
  return String(value || "").trim().replace(/[–—]/g, "-");
}

function formationValidePourEdition(value) {
  const normalisee = normaliserFormation(value);
  return /^\d+(?:-\d+)+$/.test(normalisee) && slotsPourFormation(normalisee).length === 11;
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
  const [placements, setPlacements] = useState({});
  const [slotPicker, setSlotPicker] = useState(null);
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
        const placementsInitiaux = {};
        (bloc.titulaires || []).forEach((joueur) => {
          choixInitial[joueur.id] = "titulaire";
          if (joueur.numero != null) numerosInitiaux[joueur.id] = String(joueur.numero);
          const placement = placementDuJoueur(joueur);
          if (placement) placementsInitiaux[joueur.id] = placement;
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
        setPlacements(placementsInitiaux);
        setSlotPicker(null);
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
    const titulairesCourants = joueurs.filter((joueur) => choix[joueur.id] === "titulaire");
    if (comptes.titulaires !== 11) {
      erreurs.push(`La composition doit contenir exactement 11 titulaires (actuellement ${comptes.titulaires}).`);
    }
    if (comptes.banc > maxBanc) erreurs.push(`La composition dépasse la limite de ${maxBanc} remplaçants.`);

    const formationNormalisee = normaliserFormation(formation);
    const formationValide = formationValidePourEdition(formationNormalisee);
    if (!formationNormalisee) {
      erreurs.push("Une formation est obligatoire pour attribuer les 11 positions.");
    } else if (!formationValide) {
      erreurs.push("La formation doit définir exactement 11 positions, par exemple 4-3-3.");
    }

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

    const positionsVues = new Map();
    titulairesCourants.forEach((joueur) => {
      const placement = placements[joueur.id];
      if (!placement) {
        erreurs.push(`${joueur.nom_complet} doit recevoir une position tactique.`);
      } else if (!formationValide || !slotValide(formationNormalisee, placement)) {
        erreurs.push(`${joueur.nom_complet} possède une position absente de la formation ${formationNormalisee || "choisie"}.`);
      } else {
        const cle = clePosition(placement.ligne_index, placement.position_index);
        if (positionsVues.has(cle)) {
          erreurs.push(`La position ${libellePosition(formationNormalisee, placement.ligne_index, placement.position_index)} est attribuée à plusieurs joueurs.`);
        } else {
          positionsVues.set(cle, joueur.nom_complet);
        }
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
    return { erreurs: [...new Set(erreurs)], avertissements: [] };
  }, [choix, comptes, eligibilites, formation, joueurs, maxBanc, numeros, placements]);

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

  function changerFormation(value) {
    if (value === formation) return;
    // Une nouvelle formation redéfinit les lignes : les anciennes places
    // ne sont jamais remappées silencieusement sur de nouveaux joueurs.
    setFormation(value);
    setPlacements({});
    setSlotPicker(null);
    marquerModifie();
  }

  function choisirRole(joueur, role) {
    if (verrouille) return;
    const actuel = choix[joueur.id];
    const eligibilite = eligibilites[joueur.id];
    if (actuel === role) {
      setChoix((ancien) => ({ ...ancien, [joueur.id]: undefined }));
      setPlacements((ancien) => {
        const suivant = { ...ancien };
        delete suivant[joueur.id];
        return suivant;
      });
      marquerModifie();
      return;
    }
    if (!formationValidePourEdition(formation)) {
      setErreur("Choisissez d'abord une formation valide avant de sélectionner les joueurs.");
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
    if (role !== "titulaire") {
      setPlacements((ancien) => {
        const suivant = { ...ancien };
        delete suivant[joueur.id];
        return suivant;
      });
    }
    marquerModifie();
  }

  function assignerPosition(joueur, value) {
    if (verrouille || choix[joueur.id] !== "titulaire") return;
    if (!formationValidePourEdition(formation)) {
      setErreur("Choisissez d'abord une formation valide pour attribuer une position.");
      return;
    }
    const placement = lireClePosition(value);
    if (!placement) {
      setPlacements((ancien) => {
        const suivant = { ...ancien };
        delete suivant[joueur.id];
        return suivant;
      });
      marquerModifie();
      return;
    }
    if (!slotValide(normaliserFormation(formation), placement)) {
      setErreur("Cette position n'existe pas dans la formation actuelle.");
      return;
    }
    const occupant = occupantPourPosition(placement, joueur.id);
    if (occupant) {
      setErreur(`${libellePosition(normaliserFormation(formation), placement.ligne_index, placement.position_index)} est déjà occupée par ${occupant.nom_complet}. Aucun joueur n'a été déplacé.`);
      return;
    }
    setPlacements((ancien) => ({ ...ancien, [joueur.id]: placement }));
    marquerModifie();
  }

  function occupantPourPosition(placement, joueurId = null) {
    return titulaires.find((autre) => (
      autre.id !== joueurId
      && placements[autre.id]
      && clePosition(placements[autre.id].ligne_index, placements[autre.id].position_index)
        === clePosition(placement.ligne_index, placement.position_index)
    ));
  }

  function ouvrirSelectionSlot(ligneIndex, positionIndex) {
    if (verrouille) return;
    if (!formationValidePourEdition(formation)) {
      setErreur("Choisissez d'abord une formation valide pour ouvrir ses positions.");
      return;
    }
    const placement = { ligne_index: ligneIndex, position_index: positionIndex };
    if (!slotValide(normaliserFormation(formation), placement)) {
      setErreur("Cette position n'existe pas dans la formation actuelle.");
      return;
    }
    setErreur("");
    setSlotPicker({
      ...placement,
      label: libellePosition(normaliserFormation(formation), ligneIndex, positionIndex),
    });
  }

  function placerJoueurDansSlot(joueur) {
    if (verrouille || !slotPicker) return;
    const placement = {
      ligne_index: slotPicker.ligne_index,
      position_index: slotPicker.position_index,
    };
    const occupant = occupantPourPosition(placement, joueur.id);
    if (occupant) {
      setErreur(`${slotPicker.label} est déjà occupée par ${occupant.nom_complet}. Aucun joueur n'a été déplacé.`);
      return;
    }
    const role = choix[joueur.id];
    if (role !== "titulaire" && joueur.compositionSeulement) {
      setErreur("Ce joueur appartient à une ancienne feuille mais n'est plus disponible dans l'effectif actuel.");
      return;
    }
    if (role !== "titulaire" && valeurStatut(eligibilites[joueur.id]) === "BLOQUANT") {
      setErreur(eligibilites[joueur.id]?.message || "Ce joueur ne peut pas être sélectionné.");
      return;
    }
    if (role !== "titulaire" && comptes.titulaires >= 11) {
      setErreur("Les 11 places sont déjà occupées. Retirez d'abord un titulaire ou utilisez une action de remplacement explicite.");
      return;
    }
    if (role === "titulaire"
      && placements[joueur.id]
      && clePosition(placements[joueur.id].ligne_index, placements[joueur.id].position_index)
        === clePosition(placement.ligne_index, placement.position_index)) {
      setSlotPicker(null);
      return;
    }
    setChoix((ancien) => ({ ...ancien, [joueur.id]: "titulaire" }));
    setPlacements((ancien) => ({ ...ancien, [joueur.id]: placement }));
    setSlotPicker(null);
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
    if (!formationValidePourEdition(formation)) return [];
    const joueursAvecPlace = titulaires.map((joueur) => ({
      ...joueur,
      ligne_index: placements[joueur.id]?.ligne_index ?? null,
      position_index: placements[joueur.id]?.position_index ?? null,
    }));
    return lignesAvecPlacements(normaliserFormation(formation), joueursAvecPlace);
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
          const placement = placements[joueur.id];
          return {
            joueur_id: joueur.id,
            statut: choix[joueur.id],
            numero: valeurNumero === "" ? null : Number(valeurNumero),
            ligne_index: placement?.ligne_index ?? null,
            position_index: placement?.position_index ?? null,
          };
        });
      const nouvelleComposition = await api.enregistrerComposition(matchId, {
        equipe,
        formation: normaliserFormation(formation) || null,
        staff_id: staffId ? Number(staffId) : null,
        joueurs: lignes,
      });
      const bloc = nouvelleComposition?.[equipe] || {};
      const choixServeur = {};
      const numerosServeur = {};
      const placementsServeur = {};
      (bloc.titulaires || []).forEach((joueur) => {
        choixServeur[joueur.id] = "titulaire";
        if (joueur.numero != null) numerosServeur[joueur.id] = String(joueur.numero);
        const placement = placementDuJoueur(joueur);
        if (placement) placementsServeur[joueur.id] = placement;
      });
      (bloc.banc || []).forEach((joueur) => {
        choixServeur[joueur.id] = "remplacant";
        if (joueur.numero != null) numerosServeur[joueur.id] = String(joueur.numero);
      });
      setCompo(nouvelleComposition);
      setChoix(choixServeur);
      setNumeros(numerosServeur);
      setPlacements(placementsServeur);
      setSlotPicker(null);
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

  const formationValide = formationValidePourEdition(formation);
  const lignesTerrain = pitchRows();
  const lignesTerrainAffichees = [...lignesTerrain].reverse();
  const positionSlots = formationValide ? slotsPourFormation(normaliserFormation(formation)) : [];
  const joueursPickerDisponibles = joueurs.filter((joueur) => (
    !choix[joueur.id]
    && !joueur.compositionSeulement
    && valeurStatut(eligibilites[joueur.id]) !== "BLOQUANT"
  ));
  const joueursPickerBanc = banc.filter((joueur) => !joueur.compositionSeulement && valeurStatut(eligibilites[joueur.id]) !== "BLOQUANT");
  const joueursPickerTitulaires = titulaires;
  const joueursPlaces = new Set(
    lignesTerrain.flatMap((ligne) => ligne.joueurs.filter(Boolean).map((joueur) => joueur.id)),
  );
  const nombreJoueursPlaces = joueursPlaces.size;
  const titulairesNonPlaces = titulaires.filter((joueur) => !joueursPlaces.has(joueur.id));
  const pourcentageTitulaires = Math.min(100, Math.round((comptes.titulaires / 11) * 100));
  const pourcentagePlaces = Math.min(100, Math.round((nombreJoueursPlaces / 11) * 100));
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
            <div><span>Titulaires</span><strong>{comptes.titulaires} / 11</strong></div>
            <div className="composition-progress"><span style={{ width: `${pourcentageTitulaires}%` }} /></div>
          </div>
          <div className="composition-counter">
            <div><span>Placés</span><strong>{nombreJoueursPlaces} / 11</strong></div>
            <div className="composition-progress composition-progress-placed"><span style={{ width: `${pourcentagePlaces}%` }} /></div>
          </div>
          <div className="composition-counter">
            <div><span>Banc</span><strong>{comptes.banc} / {maxBanc}</strong></div>
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
      {!verrouille && !formationValide && (
        <div className="composition-alert composition-alert-info" role="status">
          <strong>Choisissez la formation en premier.</strong>
          <span>Les joueurs pourront ensuite être affectés à des places explicites. Aucun déplacement automatique n'est effectué.</span>
        </div>
      )}
      {avertissements.map((avertissement) => (
        <div key={avertissement} className="composition-alert composition-alert-warning" role="status">
          <span>{avertissement}</span>
        </div>
      ))}
      {titulaires.length > 0 && titulairesNonPlaces.length > 0 && (
        <div className="composition-alert composition-alert-warning" role="status">
          <strong>Placement tactique incomplet</strong>
          <span>Cette feuille ne peut pas être présentée comme un onze officiel tant que chaque titulaire n'a pas une position distincte.</span>
        </div>
      )}
      {validation.avertissements.map((avertissement) => (
        <div key={avertissement} className="composition-alert composition-alert-info" role="status">
          <span>{avertissement}</span>
        </div>
      ))}
      {message && <p className="composition-feedback composition-feedback-ok" role="status">{message}</p>}
      {erreur && <p className="composition-feedback composition-feedback-error" role="alert">{erreur}</p>}

      <section className="composition-selected-summary" aria-label="Joueurs sélectionnés">
        <div className="composition-section-heading">
          <div><p className="composition-eyebrow">Feuille du match</p><h2>Noms et positions sélectionnés</h2></div>
          <span className="composition-section-count">Poste habituel ≠ place du match</span>
        </div>
        <div className="composition-selected-grid">
          <div className="composition-selected-column">
            <div className="composition-selected-title"><strong>Titulaires</strong><span>{titulaires.length}/11</span></div>
            {titulaires.length ? (
              <ol className="composition-selected-list">
                {titulaires.map((joueur) => {
                  const placement = placements[joueur.id];
                  return (
                    <li key={joueur.id}>
                      <span className="composition-selected-number">{numeros[joueur.id] || joueur.numero || "—"}</span>
                      <span>
                        <strong>{joueur.nom_complet}</strong>
                        <small>{placement && slotValide(normaliserFormation(formation), placement) ? libellePosition(normaliserFormation(formation), placement.ligne_index, placement.position_index) : "Position à attribuer"}</small>
                      </span>
                    </li>
                  );
                })}
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
              onChange={(event) => changerFormation(event.target.value)}
              disabled={verrouille}
              aria-describedby="formation-help"
            >
              <option value="">— Choisir une formation —</option>
              {FORMATIONS.map((modele) => <option key={modele} value={modele}>{modele}</option>)}
              {formation && !FORMATIONS.includes(formation) && <option value={formation}>{formation} · ancienne valeur</option>}
            </select>
            <small id="formation-help">La formation définit les slots disponibles. Aucun joueur n'est déplacé automatiquement : attribuez une position à chaque titulaire.</small>
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
            <button key={modele} type="button" className={formation === modele ? "is-active" : ""} onClick={() => changerFormation(modele)} disabled={verrouille}>
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
        <p className="composition-help">Aperçu construit uniquement depuis les positions choisies pour ce match. Le poste habituel du joueur n'impose plus sa ligne.</p>
        <div className="composition-pitch">
          <div className="composition-pitch-center-line" />
          <div className="composition-pitch-circle" />
          <div className="composition-pitch-rows">
            {lignesTerrainAffichees.map((ligne) => (
              <div className="composition-pitch-row" key={`${ligne.label}-${ligne.poste}-${ligne.ligneIndex}`}>
                {Array.from({ length: ligne.places }).map((_, index) => {
                  const joueur = joueurPourSlot(ligne.joueurs, index);
                  const positionLabel = libellePosition(normaliserFormation(formation), ligne.ligneIndex, index);
                  return joueur ? (
                    <span className="composition-pitch-player" key={joueur.id} title={`${joueur.nom_complet} · ${positionLabel}`}>
                      <b>{numeros[joueur.id] || joueur.numero || "—"}</b>
                      <small>{nomCourt(joueur.nom_complet)}</small>
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="composition-pitch-empty"
                      key={`${ligne.label}-vide-${index}`}
                      onClick={() => ouvrirSelectionSlot(ligne.ligneIndex, index)}
                      disabled={verrouille || !formationValide}
                      aria-label={`Ajouter un joueur à ${positionLabel}`}
                      title={`Ajouter un joueur à ${positionLabel}`}
                    >
                      +
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
        {slotPicker && (
          <section className="composition-slot-picker" aria-label={`Choisir un joueur pour ${slotPicker.label}`}>
            <div className="composition-slot-picker-head">
              <div>
                <p className="composition-eyebrow">Position libre</p>
                <strong>{slotPicker.label}</strong>
              </div>
              <button type="button" className="composition-slot-picker-close" onClick={() => setSlotPicker(null)} aria-label="Fermer la sélection">
                Fermer
              </button>
            </div>
            {joueursPickerDisponibles.length > 0 && (
              <div className="composition-picker-group">
                <span className="composition-picker-group-title">Joueurs disponibles</span>
                <div className="composition-picker-list">
                  {joueursPickerDisponibles.map((joueur) => (
                    <button key={joueur.id} type="button" className="composition-picker-player" onClick={() => placerJoueurDansSlot(joueur)}>
                      <strong>{joueur.nom_complet}</strong>
                      <small>{labelPoste(joueur.poste) || "Poste non renseigné"} · Placer ici</small>
                    </button>
                  ))}
                </div>
              </div>
            )}
            {joueursPickerBanc.length > 0 && (
              <div className="composition-picker-group">
                <span className="composition-picker-group-title">Remplaçants déclarés</span>
                <div className="composition-picker-list">
                  {joueursPickerBanc.map((joueur) => (
                    <button key={joueur.id} type="button" className="composition-picker-player" onClick={() => placerJoueurDansSlot(joueur)}>
                      <strong>{joueur.nom_complet}</strong>
                      <small>Passer titulaire ici</small>
                    </button>
                  ))}
                </div>
              </div>
            )}
            {joueursPickerTitulaires.length > 0 && (
              <div className="composition-picker-group">
                <span className="composition-picker-group-title">Titulaires déjà choisis</span>
                <div className="composition-picker-list">
                  {joueursPickerTitulaires.map((joueur) => (
                    <button key={joueur.id} type="button" className="composition-picker-player" onClick={() => placerJoueurDansSlot(joueur)}>
                      <strong>{joueur.nom_complet}</strong>
                      <small>{placements[joueur.id] && slotValide(normaliserFormation(formation), placements[joueur.id]) ? `Déplacer ici · ${libellePosition(normaliserFormation(formation), placements[joueur.id].ligne_index, placements[joueur.id].position_index)}` : "Placer ici"}</small>
                    </button>
                  ))}
                </div>
              </div>
            )}
            {!joueursPickerDisponibles.length && !joueursPickerBanc.length && !joueursPickerTitulaires.length && (
              <p className="composition-selected-empty">Aucun joueur disponible pour cette position.</p>
            )}
          </section>
        )}
        {titulairesNonPlaces.length > 0 && (
          <p className="composition-unplaced">Joueurs titulaires sans position valide : {titulairesNonPlaces.map((joueur) => joueur.nom_complet).join(", ")}</p>
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
              const placement = placements[joueur.id];
              const positionValue = placement && slotValide(normaliserFormation(formation), placement)
                ? clePosition(placement.ligne_index, placement.position_index)
                : "";
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
                    {role === "titulaire" ? (
                      <label className="composition-position-field">
                        <span>Position pour ce match</span>
                        <select
                          value={positionValue}
                          onChange={(event) => assignerPosition(joueur, event.target.value)}
                          disabled={verrouille}
                          aria-label={`Position de ${joueur.nom_complet} pour ce match`}
                        >
                          <option value="">— Choisir une position —</option>
                          {positionSlots.map((slot) => {
                            const occupant = titulaires.find((autre) => (
                              autre.id !== joueur.id
                              && placements[autre.id]
                              && clePosition(placements[autre.id].ligne_index, placements[autre.id].position_index) === slot.key
                            ));
                            return (
                              <option key={slot.key} value={slot.key} disabled={Boolean(occupant)}>
                                {slot.label}{occupant ? ` · occupée par ${occupant.nom_complet}` : ""}
                              </option>
                            );
                          })}
                        </select>
                      </label>
                    ) : role === "remplacant" ? (
                      <small className="composition-bench-position">Remplaçant : aucune position de titulaire</small>
                    ) : null}
                  </div>
                  <label className="composition-number-field">
                    <span>N°</span>
                    <input type="number" min="1" max="99" inputMode="numeric" value={numero} onChange={(event) => modifierNumero(joueur.id, event.target.value)} disabled={verrouille} aria-label={`Numéro de ${joueur.nom_complet}`} />
                  </label>
                  <div className="composition-player-actions">
                    <button type="button" className={role === "titulaire" ? "is-active" : ""} onClick={() => choisirRole(joueur, "titulaire")} disabled={verrouille || (!role && !formationValide) || (bloquant && !role)}>
                      Titulaire
                    </button>
                    <button type="button" className={role === "remplacant" ? "is-active" : ""} onClick={() => choisirRole(joueur, "remplacant")} disabled={verrouille || (!role && !formationValide) || (bloquant && !role)}>
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
          {sauvegardeEnCours ? "Enregistrement…" : verrouille ? "Match verrouillé" : "Enregistrer la composition"}
        </button>
      </div>
    </section>
  );
}
