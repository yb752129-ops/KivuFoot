const RANGS = [
  { key: "gk", n: 1, postes: ["gardien"] },
  { key: "def", n: 4, postes: ["defenseur"] },
  { key: "mid", n: 3, postes: ["milieu"] },
  { key: "fwd", n: 3, postes: ["attaquant"] },
];

function ranger(titulaires, byId) {
  const used = new Set();
  const rows = RANGS.map((row) => {
    const slots = [];
    for (const p of titulaires) {
      if (slots.length >= row.n) break;
      const poste = byId[p.joueur_id]?.poste;
      if (row.postes.includes(poste) && !used.has(p.joueur_id)) {
        used.add(p.joueur_id);
        slots.push(p);
      }
    }
    return { ...row, slots };
  });
  const rest = titulaires.filter((p) => !used.has(p.joueur_id));
  for (const row of rows) {
    while (row.slots.length < row.n && rest.length) {
      const p = rest.shift();
      used.add(p.joueur_id);
      row.slots.push(p);
    }
  }
  return rows.map((row) => {
    const filled = [...row.slots];
    while (filled.length < row.n) filled.push(null);
    return filled;
  });
}

function Pion({ p, nom }) {
  const label = p ? nom(p.joueur_id) : "";
  return (
    <span className="pion">
      <span className="pion-disque" />
      <span className="pion-nom">{label || "\u00a0"}</span>
    </span>
  );
}

function Demi({ titre, titulaires, banc, nom, byId, inverse }) {
  const lignes = ranger(titulaires, byId);
  const ordre = inverse ? [...lignes].reverse() : lignes;
  return (
    <div className="pitch-demi">
      <p className="pitch-club">{titre}</p>
      {ordre.map((row, i) => (
        <div key={i} className="pitch-rang">
          {row.map((p, j) => (
            <Pion key={p ? p.joueur_id : `v-${i}-${j}`} p={p} nom={nom} />
          ))}
        </div>
      ))}
      <p className="pitch-coach">Entraîneur · à compléter</p>
      <p className="pitch-banc">
        Banc · {banc.length ? banc.map((p) => nom(p.joueur_id)).join(" · ") : "à compléter"}
      </p>
    </div>
  );
}

export default function Terrain({ home, away, parts, nom, byId }) {
  const titu = (cote) => (parts || []).filter((p) => p.equipe_concernee === cote && p.statut === "titulaire");
  const banc = (cote) => (parts || []).filter((p) => p.equipe_concernee === cote && p.statut === "remplacant");
  const n = (parts || []).filter((p) => p.statut === "titulaire").length;

  return (
    <div className="pitch">
      <Demi
        titre={away || "Extérieur"}
        titulaires={titu("exterieur")}
        banc={banc("exterieur")}
        nom={nom}
        byId={byId}
        inverse
      />
      <div className="pitch-milieu" aria-hidden="true" />
      <Demi
        titre={home || "Domicile"}
        titulaires={titu("domicile")}
        banc={banc("domicile")}
        nom={nom}
        byId={byId}
      />
      {n === 0 && <p className="pitch-vide">Composition à compléter</p>}
    </div>
  );
}
