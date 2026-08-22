/**
 * KIVUFOOT — Bot de diffusion Telegram
 *
 * Principe : ce script tourne côté SERVEUR (Node.js), jamais sur le
 * téléphone du correspondant. Il écoute les nouveaux événements validés
 * dans Supabase (Realtime) et les publie automatiquement sur le canal
 * Telegram du championnat.
 *
 * WhatsApp : la diffusion WhatsApp automatique nécessite un compte
 * WhatsApp Business API (Meta), payant et à valider par Meta — prévu en
 * phase 2. En attendant, ce bot Telegram couvre le même besoin
 * (diffusion instantanée, gratuite, fiable) et un lien "Suivre sur
 * Telegram" peut être partagé sur WhatsApp.
 *
 * Installation :
 *   npm install @supabase/supabase-js node-telegram-bot-api dotenv
 *   node diffusion.js
 */

import { createClient } from '@supabase/supabase-js'
import TelegramBot from 'node-telegram-bot-api'
import 'dotenv/config'

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY // clé service (serveur uniquement, jamais côté client)
)

const bot = new TelegramBot(process.env.TELEGRAM_BOT_TOKEN, { polling: false })
const CHAT_ID = process.env.TELEGRAM_CHANNEL_ID

const EMOJI = {
  but: '⚽',
  carton: '🟨',
  remplacement: '🔁',
  debut: '🟢',
  fin: '🏁',
}

async function formatMessage(evenement) {
  const { data: match } = await supabase
    .from('matchs')
    .select('*, club_domicile:club_domicile_id(nom), club_exterieur:club_exterieur_id(nom)')
    .eq('id', evenement.match_id)
    .single()

  if (!match) return null

  const emoji = EMOJI[evenement.type] || '📋'
  const entete = `${emoji} ${evenement.type.toUpperCase()}`
  const score = `${match.club_domicile.nom} ${match.score_domicile}-${match.score_exterieur} ${match.club_exterieur.nom}`
  const minute = evenement.minute ? ` (${evenement.minute}')` : ''

  return `${entete}\n${score}${minute}`
}

async function diffuser(evenement) {
  const message = await formatMessage(evenement)
  if (!message) return
  try {
    await bot.sendMessage(CHAT_ID, message)
    console.log('[diffusion] envoyé:', message.replace('\n', ' | '))
  } catch (err) {
    console.error('[diffusion] échec envoi Telegram, nouvelle tentative dans 5s', err.message)
    setTimeout(() => diffuser(evenement), 5000)
  }
}

// Écoute en temps réel : dès qu'un événement passe au statut "vérifié", on diffuse.
supabase
  .channel('evenements-verifies')
  .on(
    'postgres_changes',
    { event: 'UPDATE', schema: 'public', table: 'evenements' },
    (payload) => {
      const before = payload.old
      const after = payload.new
      if (before.statut !== 'vérifié' && after.statut === 'vérifié') {
        diffuser(after)
      }
    }
  )
  .subscribe((status) => {
    console.log('[diffusion] statut abonnement Supabase Realtime:', status)
  })

console.log('KivuFoot — bot de diffusion démarré. En attente d\'événements vérifiés…')
