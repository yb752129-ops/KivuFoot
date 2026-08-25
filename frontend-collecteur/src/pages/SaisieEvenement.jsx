import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useLiveQuery } from "dexie-react-hooks";
import { db } from "../lib/db";
import { synchroniser } from "../lib/sync";
import IndicateurSync from "../components/IndicateurSync";

const TYPES_EVENEMENT = [
  { value: "but", label: "But", requiertSecondaire: false, requiertResultat: false },
  { value: "but_contre_son_camp", label: "But contre son camp", requiertSecondaire: false, requiertResultat: false },
  { value: "passe_decisive", label: "Passe décisive", requiertSecondaire: true, requiertResultat: false },
  { value: "carton_jaune", label: "Carton jaune", requiertSecondaire: false, requiertResultat: false },
  { value: "carton_rouge", label: "Carton rouge", requiertSecondaire: false, requiertResultat: false },
  { value: "remplacement", label: "Remplacement", requiertSecondaire: true, requiertResultat: false },
  { value: "penalty", label: "Penalty", requiertSecondaire: false, requiertResultat: true },
];

function genererUuid() {
  return crypto.randomUUID();
}

export default function SaisieEvenement() {
  const { matchId } = useParams();
  const [type, setType] = useState("but");
  const [minute, setMinute] = useState("");
  const [joueurId, setJoueurId] = useState("");
  const [joueurSecondaireId, setJoueurSecondaireId] = useState("");
  const [resultat, setResultat] = useState("marque");
  const [equipeConcernee, setEquipeConcernee] = useState("domicile");
  const [confirmation, setConfirmation] = useState(null);

  const evenementsDuMatch = useLiveQuery(
    () => db.evenementsLocaux.where("matchId").equals(Number(matchId)).reverse().toArray(),
    [matchId]
  );

  const typeConfig = TYPES_EVENEMENT.find((t) => t.value === type);

  useEffect(() => {
    synchroniser();
  }, []);

  async function onSubmit(e) {
    e.preventDefault();
    const tempId = genererUuid();

    // Écriture LOCALE IMMÉDIATE (§5.1 point 4) : la saisie n'attend jamais le réseau.
    await db.evenementsLocaux.add({
      tempId,
      matchId: Number(matchId),
      minute: Number(minute),
      type,
      joueurId: joueurId ? Number(joueurId) : null,
      joueurSecondaireId: typeConfig.requiertSecondaire && joueurSecondaireId ? Number(joueurSecondaireId) : null,
      resultat: typeConfig.requiertResultat ? resultat : null,
      equipeConcernee,
      statutSync: "local",
      createdAt: new Date().toISOString(),
    });

    setConfirmation("Événement enregistré localement. Synchronisation en cours dès que possible.");
    setMinute("");
    setJoueurId("");
    setJoueurSecondaireId("");

    // Tentative de synchronisation immédiate (silencieuse si hors-ligne).
    synchroniser();
  }

  return (
    <div className="page page-saisie">
      <header>
        <h1>Match #{matchId} — Saisie</h1>
        <IndicateurSync />
      </header>

      <form onSubmit={onSubmit} className="form-evenement">
        <label>
          Type d'événement
          <select value={type} onChange={(e) => setType(e.target.value)}>
            {TYPES_EVENEMENT.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          Minute
          <input type="number" min="0" max="130" value={minute} onChange={(e) => setMinute(e.target.value)} required />
        </label>

        <label>
          Équipe concernée
          <select value={equipeConcernee} onChange={(e) => setEquipeConcernee(e.target.value)}>
            <option value="domicile">Domicile</option>
            <option value="exterieur">Extérieur</option>
          </select>
        </label>

        <label>
          Joueur {type === "remplacement" ? "(sortant)" : ""}
          <input
            type="number"
            placeholder="ID joueur"
            value={joueurId}
            onChange={(e) => setJoueurId(e.target.value)}
            required
          />
        </label>

        {typeConfig.requiertSecondaire && (
          <label>
            {type === "remplacement" ? "Joueur entrant" : "Passeur"}
            <input
              type="number"
              placeholder="ID joueur"
              value={joueurSecondaireId}
              onChange={(e) => setJoueurSecondaireId(e.target.value)}
              required
            />
          </label>
        )}

        {typeConfig.requiertResultat && (
          <label>
            Résultat
            <select value={resultat} onChange={(e) => setResultat(e.target.value)}>
              <option value="marque">Marqué</option>
              <option value="rate">Raté</option>
            </select>
          </label>
        )}

        <button type="submit">Enregistrer</button>
        {confirmation && <p className="confirmation">{confirmation}</p>}
      </form>

      <section className="liste-evenements-locaux">
        <h2>Événements saisis pour ce match</h2>
        <ul>
          {(evenementsDuMatch || []).map((ev) => (
            <li key={ev.tempId} className={`statut-${ev.statutSync}`}>
              {ev.minute}' — {ev.type} — {ev.statutSync}
              {ev.messageServeur && <span className="message-serveur"> ({ev.messageServeur})</span>}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
