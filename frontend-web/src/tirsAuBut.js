export const PHASES_ELIMINATOIRES = ["barrage", "quart", "demi", "finale"];

export function scoreTirsAuBut(tirs = []) {
  return (tirs || []).reduce((score, tir) => {
    const equipe = tir?.equipe_concernee;
    if (equipe === "domicile" || equipe === "exterieur") {
      if (tir.resultat === "marque") score[equipe] += 1;
    }
    return score;
  }, { domicile: 0, exterieur: 0 });
}

export function vainqueurTirsAuBut(tirs = []) {
  const score = scoreTirsAuBut(tirs);
  const tirsEquipe = { domicile: 0, exterieur: 0 };
  for (const tir of tirs || []) {
    if (tir?.equipe_concernee === "domicile" || tir?.equipe_concernee === "exterieur") {
      tirsEquipe[tir.equipe_concernee] += 1;
    }
  }
  const hn = tirsEquipe.domicile;
  const an = tirsEquipe.exterieur;
  const hg = score.domicile;
  const ag = score.exterieur;
  if (hn <= 5 && an <= 5) {
    if (hg > ag + (5 - an)) return "domicile";
    if (ag > hg + (5 - hn)) return "exterieur";
    if (hn === 5 && an === 5 && hg !== ag) return hg > ag ? "domicile" : "exterieur";
    return null;
  }
  if (hn === an && hn >= 5 && hg !== ag) return hg > ag ? "domicile" : "exterieur";
  if (hn === an + 1 && hg > ag + 1) return "domicile";
  if (an === hn + 1 && ag > hg + 1) return "exterieur";
  return null;
}
