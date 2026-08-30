# KivuFoot — site public + organisateur

Interface unique (Phase 5 + 6) :

- public : résultats, classement, clubs, buteurs
- `/login` puis `/orga` : validation et publication

## Build

```bash
cp .env.example .env
# VITE_API_BASE_URL=https://kivufoot.onrender.com/api/v1
npm install
npm run build
```

Render Static Site : Root Directory `frontend-web`, build `npm install && npm run build`, publish `dist`.
