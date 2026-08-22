import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'

function StatutBadge({ statut }) {
  if (statut === 'vérifié') return <span className="badge-verifie">✓ Vérifié</span>
  if (statut === 'en_vérification') return <span className="badge-en-verif">⏳ En vérification</span>
  return <span className="badge-attente">• En attente</span>
}

export default function Public() {
  const [matchsLive, setMatchsLive] = useState([])
  const [classement, setClassement] = useState([])
  const [derniereMaj, setDerniereMaj] = useState(null)

  const charger = async () => {
    const { data: matchs } = await supabase
      .from('matchs')
      .select('*, club_domicile:club_domicile_id(nom), club_exterieur:club_exterieur_id(nom)')
      .in('statut', ['live', 'mi_temps', 'termine'])
      .order('date_heure', { ascending: false })
      .limit(10)
    setMatchsLive(matchs || [])
    setDerniereMaj(new Date())

    const { data: cls } = await supabase.from('classement').select('*').order('victoires', { ascending: false })
    setClassement(cls || [])
  }

  useEffect(() => {
    charger()
    const interval = setInterval(charger, 15000) // rafraîchit toutes les 15s
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen p-4 max-w-2xl mx-auto">
      <header className="text-center mb-8 pt-6">
        <h1 className="font-display text-5xl tracking-wide text-gold">KIVUFOOT</h1>
        <p className="text-chalk/60 text-sm mt-1">Le championnat d'Uvira, en direct</p>
      </header>

      <section className="mb-10">
        <h2 className="font-display text-xl tracking-widest text-chalk/70 mb-3">MATCHS</h2>
        <div className="space-y-3">
          {matchsLive.length === 0 && (
            <p className="text-chalk/40 text-sm">Aucun match en cours pour l'instant.</p>
          )}
          {matchsLive.map((m) => (
            <div key={m.id} className="bg-pitchLine rounded-2xl p-4 border border-chalk/10">
              <div className="flex justify-between items-center">
                <span className="font-medium">{m.club_domicile?.nom}</span>
                <span className="font-display text-2xl text-gold">
                  {m.score_domicile} – {m.score_exterieur}
                </span>
                <span className="font-medium">{m.club_exterieur?.nom}</span>
              </div>
              <div className="flex justify-between items-center mt-2">
                <StatutBadge statut={m.score_statut} />
                <span className="text-xs text-chalk/40">
                  {m.statut === 'live' ? '🔴 En direct' : m.statut === 'termine' ? 'Terminé' : m.statut}
                </span>
              </div>
            </div>
          ))}
        </div>
        {derniereMaj && (
          <p className="text-xs text-chalk/30 mt-3">
            Dernière mise à jour il y a {Math.floor((Date.now() - derniereMaj) / 1000)}s
          </p>
        )}
      </section>

      <section>
        <h2 className="font-display text-xl tracking-widest text-chalk/70 mb-3">CLASSEMENT</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-chalk/40 text-left border-b border-chalk/10">
              <th className="py-2">Club</th>
              <th>J</th><th>V</th><th>N</th><th>D</th><th>BM</th><th>BE</th>
            </tr>
          </thead>
          <tbody>
            {classement.map((c) => (
              <tr key={c.club_id} className="border-b border-chalk/5">
                <td className="py-2 font-medium">{c.club_nom}</td>
                <td>{c.matchs_joues}</td>
                <td className="text-gold">{c.victoires}</td>
                <td>{c.nuls}</td>
                <td>{c.defaites}</td>
                <td>{c.buts_marques}</td>
                <td>{c.buts_encaisses}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="text-xs text-chalk/30 mt-3">
          Classement calculé uniquement sur les résultats au statut "Vérifié".
        </p>
      </section>
    </div>
  )
}
