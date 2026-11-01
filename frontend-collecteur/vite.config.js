import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import { cpus } from "node:os";

// Android/Termux may report zero CPUs; Workbox's Terser worker pool then
// never starts. Keep production minification elsewhere, with a safe fallback.
const modeWorkbox = cpus().length === 0 ? "development" : "production";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      // Mise en cache locale des matchs/clubs/joueurs consultés (§12.3) via
      // le cache du Service Worker pour les requêtes GET de l'API.
      workbox: {
        mode: modeWorkbox,
        runtimeCaching: [
          {
            urlPattern: /\/api\/v1\/(clubs|joueurs|matchs)/,
            handler: "NetworkFirst",
            options: {
              cacheName: "kivufoot-api-cache",
              networkTimeoutSeconds: 3,
              expiration: { maxEntries: 200, maxAgeSeconds: 60 * 60 * 24 },
            },
          },
        ],
      },
      manifest: {
        name: "KivuFoot Collecteur",
        short_name: "KivuFoot",
        description: "Application de saisie terrain hors-ligne pour les collecteurs KivuFoot",
        theme_color: "#0b6e4f",
        background_color: "#ffffff",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png" },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    host: true,
  },
});
