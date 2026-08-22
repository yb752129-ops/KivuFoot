import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import { enqueueEvenement, startQueueWorker, getQueue } from '../lib/queue'

const TYPES = [
  { key: 'but', label: 'BUT', emoji: '⚽' },
  { key: 'carton', label: 'CARTON', emoji: '🟨' },
  { key: 'remplacement', label: 'REMPLACEMENT', emoji: '🔁' },
  { key: 'fin', label: 'FIN', emoji: '🏁' },
]

export default function Correspondant() {
  const { matchId } = useParams()
  const [match, setMatch] = useState(null)
  const [correspondantId, setCorrespondantId] = useState(
    localStorage.getItem('kivufoot_correspondant_id') || ''
  )
  const [pending, setPending] = useState([])
  const [minuteManuelle, setMinuteManuelle] = useState('')
  const [debutMatch, setDebutMatch] = useState(null)
  const [modal, setModal] = useState(null) // { type }
  const [clubChoisi, setClubChoisi] = useState(null)
  const [feedback, setFeedback] = useState('')

  useEffect(() => {
    startQueueWorker(setPending)
    setPending(getQueue())
  }, [])

  useEffect(() => {
    if (!matchId) return
    supabase
      .from('matchs')
      .select('*, club_domicile:club_domicile_id(id,nom), club_exterieur:club_exterieur_id(id,nom)')
      .eq('id', matchId)
      .single()
      .then(({ data }) => setMatch(data))
  }, [matchId])

  const minuteActuelle = () => {
    if (minuteManuelle) return parseInt(minuteManuelle, 10)
    if (!debutMatch) return 0
    return Math.floor((Date.now() - debutMatch) / 60000)
  }

  const envoyer = (type, extra = {}) => {
    if (!correspondantId) {
      setFeedback("Renseigne d'abord ton identifiant correspondant en haut de page.")
      return
    }
    const evenement = {
      match_id: matchId,
      type,
      minute: minuteActuelle(),
      correspondant_id: correspondantId,
      statut: 'en_attente',
      soumis_le: new Date().toISOString(),
      historique: [],
      ...extra,
    }
    enqueueEvenement(evenement)
    setPending(getQueue())
    setModal(null)
    setClubChoisi(null)
    setFeedback(`${type.toUpperCase()} enregistré — envoi en cours…`)
    setTimeout(() => setFeedback(''), 2500)
  }

  if (!match) {
    return (
      <div className="min-h-screen flex items-center justify-center text-chalk/60">
        Chargement du match…
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col p-4 max-w-md mx-auto">
      {/* Identifiant correspondant */}
      <input
        className="bg-pitchLine text-chalk text-sm rounded-lg px-3 py-2 mb-3 border border-chalk/10"
        placeholder="Ton identifiant correspondant"
        value={correspondantId}
        onChange={(e) => {
          setCorrespondantId(e.target.value)
          localStorage.setItem('kivufoot_correspondant_id', e.target.value)
        }}
      />

      {/* En-tête match */}
      <div className="text-center mb-4">
        <p className="text-chalk/50 text-xs uppercase tracking-widest mb-1">Match en cours</p>
        <h1 className="font-display text-3xl tracking-wide">
          {match.club_domicile?.nom} {match.score_domicile}–{match.score_exterieur} {match.club_exterieur?.nom}
        </h1>
        <p className="text-gold text-sm mt-1">{minuteActuelle()}′</p>
      </div>

      {!debutMatch && (
        <button
          onClick={() => {
            setDebutMatch(Date.now())
            envoyer('debut')
          }}
          className="bg-gold text-pitch font-display text-xl tracking-widest rounded-xl py-4 mb-4"
        >
          DÉMARRER LE MATCH
        </button>
      )}

      {/* 4 boutons principaux */}
      <div className="grid grid-cols-2 gap-3 mt-2">
        {TYPES.map((t) => (
          <button
            key={t.key}
            disabled={!debutMatch}
            onClick={() => setModal({ type: t.key })}
            className="bg-pitchLine disabled:opacity-30 border border-chalk/10 rounded-2xl py-8 flex flex-col items-center gap-2 active:scale-95 transition"
          >
            <span className="text-3xl">{t.emoji}</span>
            <span className="font-display text-lg tracking-widest">{t.label}</span>
          </button>
        ))}
      </div>

      {/* Minute manuelle (si auto-détection à corriger) */}
      <div className="mt-4">
        <label className="text-xs text-chalk/50">Corriger la minute (optionnel)</label>
        <input
          type="number"
          className="w-full bg-pitchLine text-chalk rounded-lg px-3 py-2 mt-1 border border-chalk/10"
          placeholder="ex: 67"
          value={minuteManuelle}
          onChange={(e) => setMinuteManuelle(e.target.value)}
        />
      </div>

      {/* File d'attente / statut envoi */}
      <div className="mt-6 text-xs text-chalk/50">
        {pending.length === 0 ? (
          <p>✅ Tout est envoyé.</p>
        ) : (
          <p>⏳ {pending.length} événement(s) en cours d'envoi (réessai automatique)…</p>
        )}
      </div>

      {feedback && (
        <div className="mt-3 text-sm text-gold text-center">{feedback}</div>
      )}

      {/* Modal choix club / joueur */}
      {modal && (
        <div className="fixed inset-0 bg-black/70 flex items-end">
          <div className="bg-pitch w-full rounded-t-3xl p-5 border-t border-chalk/10">
            <h2 className="font-display text-2xl mb-4">Quel club ?</h2>
            <div className="grid grid-cols-2 gap-3 mb-4">
              {[match.club_domicile, match.club_exterieur].map((c) => (
                <button
                  key={c.id}
                  onClick={() => setClubChoisi(c.id)}
                  className={`rounded-xl py-4 border ${
                    clubChoisi === c.id ? 'border-gold bg-gold/10' : 'border-chalk/10'
                  }`}
                >
                  {c.nom}
                </button>
              ))}
            </div>
            <button
              disabled={!clubChoisi}
              onClick={() => envoyer(modal.type, { club_id: clubChoisi })}
              className="w-full bg-gold disabled:opacity-30 text-pitch font-display text-lg tracking-widest rounded-xl py-3"
            >
              CONFIRMER
            </button>
            <button
              onClick={() => { setModal(null); setClubChoisi(null) }}
              className="w-full text-chalk/50 text-sm mt-3"
            >
              Annuler
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
