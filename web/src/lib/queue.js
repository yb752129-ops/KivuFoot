// File d'attente locale + retry automatique.
// Chaque événement saisi par le correspondant est stocké localement AVANT
// toute tentative d'envoi. Si le réseau coupe, rien n'est perdu : la file
// réessaie toutes les 4 secondes jusqu'à confirmation du serveur.

import { supabase } from './supabase'

const STORAGE_KEY = 'kivufoot_queue_v1'

function readQueue() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  } catch {
    return []
  }
}

function writeQueue(queue) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(queue))
}

export function enqueueEvenement(evenement) {
  const queue = readQueue()
  const item = {
    ...evenement,
    _localId: crypto.randomUUID(),
    _tentatives: 0,
  }
  queue.push(item)
  writeQueue(queue)
  return item._localId
}

export function getQueue() {
  return readQueue()
}

async function trySend(item) {
  const { _localId, _tentatives, ...payload } = item
  const { error } = await supabase.from('evenements').insert(payload)
  return !error
}

let running = false

export function startQueueWorker(onUpdate) {
  if (running) return
  running = true

  const tick = async () => {
    const queue = readQueue()
    if (queue.length === 0) {
      onUpdate?.(queue)
      setTimeout(tick, 4000)
      return
    }

    const next = queue[0]
    const ok = await trySend(next)

    if (ok) {
      const remaining = readQueue().filter((q) => q._localId !== next._localId)
      writeQueue(remaining)
      onUpdate?.(remaining)
    } else {
      const updated = readQueue().map((q) =>
        q._localId === next._localId ? { ...q, _tentatives: q._tentatives + 1 } : q
      )
      writeQueue(updated)
      onUpdate?.(updated)
    }

    setTimeout(tick, 4000)
  }

  tick()
}
