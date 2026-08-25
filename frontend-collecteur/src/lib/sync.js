import { db } from "./db";
import { pushEvenements } from "./api";

/**
 * Tente de synchroniser tous les événements locaux non encore confirmés.
 * Appelée : au lancement de l'app, périodiquement, et à la détection
 * d'un retour de connexion (`window.addEventListener('online', ...)`).
 *
 * Ne bloque jamais l'UI : les erreurs réseau laissent simplement les
 * événements en statut 'local' pour un prochain essai (§6.2 : push
 * automatique en arrière-plan dès que le réseau est disponible).
 */
export async function synchroniser() {
  if (!navigator.onLine) return { synchronises: 0, erreurs: 0 };

  const enAttente = await db.evenementsLocaux.where("statutSync").equals("local").toArray();
  if (enAttente.length === 0) return { synchronises: 0, erreurs: 0 };

  const items = enAttente.map((e) => ({
    type: "evenement",
    match_id: e.matchId,
    evenement: {
      temp_id: e.tempId,
      minute: e.minute,
      type: e.type,
      joueur_id: e.joueurId,
      joueur_secondaire_id: e.joueurSecondaireId ?? null,
      resultat: e.resultat ?? null,
      equipe_concernee: e.equipeConcernee,
    },
  }));

  try {
    const reponse = await pushEvenements(items);
    let synchronises = 0;
    let erreurs = 0;
    for (const resultat of reponse.resultats) {
      const local = enAttente.find((e) => e.tempId === resultat.temp_id);
      if (!local) continue;
      if (resultat.statut === "confirme") {
        await db.evenementsLocaux.update(local.tempId, {
          statutSync: resultat.erreur ? "rejete" : "confirme",
          messageServeur: resultat.erreur || null,
          evenementServeurId: resultat.evenement_id,
        });
        synchronises += 1;
      } else {
        erreurs += 1;
      }
    }
    return { synchronises, erreurs };
  } catch (err) {
    // Réseau indisponible ou erreur serveur : on retentera plus tard,
    // les données restent en sécurité dans IndexedDB.
    console.warn("Synchronisation différée :", err.message);
    return { synchronises: 0, erreurs: 0, horsLigne: true };
  }
}

export function demarrerSyncPeriodique(intervalleMs = 30000) {
  const id = setInterval(synchroniser, intervalleMs);
  window.addEventListener("online", synchroniser);
  return () => {
    clearInterval(id);
    window.removeEventListener("online", synchroniser);
  };
}
