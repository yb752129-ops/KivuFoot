import Dexie from "dexie";

/**
 * Base IndexedDB locale du collecteur.
 *
 * `evenementsLocaux` est la file d'attente offline-first (§5.1, §6.1) :
 * chaque saisie y est écrite IMMÉDIATEMENT, avec un `tempId` (UUID)
 * généré côté client. La synchronisation vers l'API se fait ensuite en
 * arrière-plan sans jamais bloquer la saisie - c'est ce qui garantit
 * que le collecteur peut travailler même sans réseau.
 *
 * statutSync : 'local' -> 'envoye' -> 'confirme' (ou 'erreur' /
 * 'conflit' / 'rejete' après retour serveur, voir lib/sync.js).
 */
export const db = new Dexie("kivufoot_collecteur");

db.version(1).stores({
  evenementsLocaux: "tempId, matchId, statutSync, createdAt",
  matchsCache: "id, statut, dateHeure",
  joueursCache: "id, clubActuelId, nomComplet",
});

export default db;
