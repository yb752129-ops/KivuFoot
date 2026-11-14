/** Détaille uniquement les listes provisoires explicitement présentes dans la note.
 * Aucun fait disciplinaire officiel n'est créé par cet affichage. */
export function detailCartonsProvisoires(matchId, note) {
  if (typeof note !== "string" || !note.includes("Cartons jaunes signalés (information provisoire)")) return null;
  const id = Number(matchId);
  let texte, cartons;
  if (id === 75) {
    texte = "• +243(SAE) : 4 cartons jaunes — 1 au coach et 3 à des joueurs non identifiés";
    cartons = ["Coach — +243(SAE)", ...Array(3).fill("Joueur non identifié — +243(SAE)")];
  } else if (id === 74) {
    texte = "• LES CHAMPIONS : Gustave\n\n• INFO-2024+2025 : Mathieu";
    cartons = ["Gustave — LES CHAMPIONS", "Mathieu — INFO-2024+2025"];
  } else return null;
  const index = note.indexOf(texte);
  if (index < 0 || note.indexOf(texte, index + texte.length) !== -1) return null;
  return { avant: note.slice(0, index).trimEnd().replace("🟨 Cartons jaunes signalés", "Cartons jaunes signalés"), cartons, apres: note.slice(index + texte.length).trimStart() };
}
