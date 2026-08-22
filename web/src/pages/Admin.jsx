import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'

export default function Admin() {
  const [evenements, setEvenements] = useState([])

  const charger = async () => {
    const { data } = await supabase
      .from('evenements')
      .select('*, match:match_id(*, club_domicile:club_domicile_id(nom), club_exterieur:club_exterieur_id(nom)), correspondant:correspondant_id(nom)')
      .in('statut', ['en_attente', 'en_vérification', 'contesté'])
      .order('soumis_le', { ascending: false })
    setEvenements(data || [])
  }

  useEffect(() => { charger() }, [])

  const valider = async (id) => {
    await supabase
      .from('evenements')
      .update({
        statut: 'vérifié',
        modifie_le: new Date().toISOString(),
      })
      .eq('id', id)
    charger()
  }

  const rejeter = async (id) => {
    await supabase
      .from('evenements')
      .update({ statut: 'contesté', modifie_le: new Date().toISOString() })
      .eq('id', id)
    charger()
  }

  return (
    <div className="min-h-screen p-4 max-w-2xl mx-auto">
      <h1 className="font-display text-3xl tracking-wide text-gold mb-6">Validation — File d'attente</h1>

      {evenements.length === 0 && (
        <p className="text-chalk/40">Rien à valider pour l'instant. Tout est à jour.</p>
      )}

      <div className="space-y-3">
        {evenements.map((e) => (
          <div key={e.id} className="bg-pitchLine rounded-xl p-4 border border-chalk/10">
            <div className="flex justify-between items-start">
              <div>
                <p className="font-medium">
                  {e.type.toUpperCase()} — {e.minute}′
                </p>
                <p className="text-sm text-chalk/60">
                  {e.match?.club_domicile?.nom} vs {e.match?.club_exterieur?.nom}
                </p>
                <p className="text-xs text-chalk/40 mt-1">
                  Source : {e.correspondant?.nom || e.correspondant_id}
                </p>
                {e.statut === 'en_vérification' && (
                  <p className="text-xs text-clay mt-1">⚠ Divergence entre correspondants — vérifier avant validation</p>
                )}
              </div>
              <div className="flex flex-col gap-2">
                <button
                  onClick={() => valider(e.id)}
                  className="bg-gold text-pitch text-xs font-semibold px-3 py-1.5 rounded-lg"
                >
                  Valider
                </button>
                <button
                  onClick={() => rejeter(e.id)}
                  className="border border-clay text-clay text-xs font-semibold px-3 py-1.5 rounded-lg"
                >
                  Rejeter
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
