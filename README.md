# KIVUFOOT — MVP

Le championnat local d'Uvira, collecté, vérifié, diffusé.

## Structure du projet

```
kivufoot/
├── supabase/schema.sql   → base de données (à exécuter dans Supabase)
├── web/                  → app React (correspondant, public, admin)
└── bot/                  → bot de diffusion Telegram (côté serveur)
```

## 1. Mettre en place la base de données (Supabase)

1. Crée un projet sur https://supabase.com (gratuit pour démarrer).
2. Va dans **SQL Editor** → colle le contenu de `supabase/schema.sql` → **Run**.
3. Dans **Project Settings → API**, récupère :
   - `Project URL` → `VITE_SUPABASE_URL`
   - `anon public key` → `VITE_SUPABASE_ANON_KEY`
   - `service_role key` (secrète, ne jamais exposer côté client) → pour le bot

4. Ajoute manuellement (via **Table Editor**) :
   - ton `championnat` (ex: "Championnat local d'Uvira")
   - la `saison` en cours, avec `couverture_depuis` = date de lancement
   - les `clubs` (les 6-8 premiers)
   - les `correspondants` (un par club)
   - les premiers `matchs` de la journée à venir

## 2. Lancer l'app web (correspondant + public + admin)

```bash
cd web
cp .env.example .env      # remplis avec tes clés Supabase
npm install
npm run dev                # développement local
```

- **Vue publique** : `/` — live, calendrier, classement
- **Vue correspondant** : `/correspondant/ID_DU_MATCH` — à ouvrir sur le téléphone du correspondant le jour du match (envoie-lui le lien direct par WhatsApp)
- **Vue admin** : `/admin` — validation/recoupement des événements en attente

**Déploiement** : `npm run build` puis déploie sur Vercel (même workflow que TelecomNexus). Ajoute les variables d'environnement dans les réglages du projet Vercel.

## 3. Lancer le bot de diffusion

```bash
cd bot
cp .env.example .env      # clés Supabase (service_role) + Telegram
npm install
npm start
```

Pour créer le bot Telegram : parle à **@BotFather** sur Telegram → `/newbot` → récupère le token. Crée ensuite un canal public (ex: `@kivufoot_uvira`) et ajoute le bot comme administrateur.

Le bot doit tourner en continu (héberge-le sur un petit serveur, Railway ou Render — gratuit pour ce volume).

## Sur WhatsApp

La diffusion automatique vers WhatsApp demande un compte **WhatsApp Business API** (validation Meta, souvent payante) — c'est prévu en phase 2, une fois le pilote validé. En attendant : partage le lien du canal Telegram dans les groupes WhatsApp existants du championnat, c'est immédiat et ça touche les mêmes gens.

## Ce qui reste à faire avant le premier match réel

- [ ] Créer le championnat, la saison, les clubs, les correspondants dans Supabase
- [ ] Tester le flux correspondant sur un faux match (vérifier que le retry fonctionne en coupant le wifi volontairement)
- [ ] Créer le bot Telegram et le canal du championnat
- [ ] Former chaque correspondant (15 min, cf. plan)
- [ ] Premier match pilote

## Rappel de la règle produit

Toute fonctionnalité qui n'est pas dans ce MVP (notation IA, valeur estimée du joueur, scouting avancé, vidéos, API) attend le jalon des 80% de couverture vérifiée sur le pilote. Voir `KivuFoot_Plan_Corrige.md`.
