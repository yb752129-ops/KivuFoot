import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn(
    'KivuFoot: variables VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY manquantes. ' +
    'Copie .env.example vers .env et remplis tes clés Supabase.'
  )
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
