const FAMILLES = ["defenseur", "milieu", "attaquant"];

function groupes(titulaires, byId) {
  const g = { gardien: [], defenseur: [], milieu: [], attaquant: [], autre: [] };
  for (const p of titulaires) {
    const poste = byId?.[p.joueur_id]?.poste;
    if (poste && g[poste]) g[poste].push(p);
    else g.autre.push(p);
  }
  let i = 0;
  while (g.autre.length) {
    g[FAMILLES[i % 3]].push(g.autre.shift());
    i += 1;
  }
  const rows = [g.gardien, g.defenseur, g.milieu, g.attaquant].filter((r) => r.length > 0);
  const totale = titulaires.length;
  const formation =
    totale === 11 ? `${g.defenseur.length}-${g.milieu.length}-${g.attaquant.length}` : null;
  return { rows, formation };
}

function Pion({ p, nom, byId }) {
  const j = byId?.[p.joueur_id];
  const label = nom(p.joueur_id);
  const num = j?.numero ?? (label ? label.trim().charAt(0).toUpperCase() : "");
  return (
    <span className="pion">
      <span className="pion-disque">{num}</span>
      <span className="pion-nom">{label || " "}</span>
    </span>
  );
}

function Demi({ titre, titulaires, banc, nom, byId, coachNom }) {
  if (titulaires.length === 0) {
    return (
      <div className="pitch-demi">
        <p className="pitch-club">{titre}</p>
        <p className="pitch-nonpubliee">Composition non publiée</p>
      </div>
    );
  }
  const { rows, formation } = groupes(titulaires, byId);
  return (
    <div className="pitch-demi">
      <p className="pitch-club">
        {titre}
        {formation && <span className="pitch-form">{formation}</span>}
      </p>
      {rows.map((row, i) => (
        <div key={i} className="pitch-rang">
          {row.map((p) => (
            <Pion key={p.joueur_id} p={p} nom={nom} byId={byId} />
          ))}
        </div>
      ))}
      {(coachNom || banc.length > 0) && (
        <div className="pitch-pied">
          {coachNom && <span className="pitch-chip">Entraîneur · {coachNom}</span>}
          {banc.length > 0 && (
            <span className="pitch-chip">Banc · {banc.map((p) => nom(p.joueur_id)).join(", ")}</span>
          )}
        </div>
      )}
    </div>
  );
}

export default function Terrain({ home, away, parts, nom, byId, coachHome, coachAway }) {
  const titu = (cote) => (parts || []).filter((p) => p.equipe_concernee === cote && p.statut === "titulaire");
  const banc = (cote) => (parts || []).filter((p) => p.equipe_concernee === cote && p.statut === "remplacant");
  const nHome = titu("domicile").length;
  const nAway = titu("exterieur").length;

  if (nHome === 0 && nAway === 0) {
    return (
      <div className="compo-vide">
        <p className="compo-vide-titre">Compositions non publiées</p>
        <p className="compo-vide-texte">
          Les compositions officielles apparaîtront ici dès leur publication par les clubs.
        </p>
      </div>
    );
  }

  return (
    <div className="pitch">
      <Demi
        titre={away || "Extérieur"}
        titulaires={titu("exterieur")}
        banc={banc("exterieur")}
        nom={nom}
        byId={byId}
        coachNom={coachAway}
      />
      <div className="pitch-milieu" aria-hidden="true" />
      <Demi
        titre={home || "Domicile"}
        titulaires={titu("domicile")}
        banc={banc("domicile")}
        nom={nom}
        byId={byId}
        coachNom={coachHome}
      />
    </div>
  );
}
