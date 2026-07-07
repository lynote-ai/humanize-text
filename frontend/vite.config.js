import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// In Docker dev mode the backend container is named `ai-humanizer`, so the
// proxy target can be overridden via API_HOST. Locally it defaults to localhost.
const API_HOST = process.env.API_HOST ?? 'http://localhost:8000'

// https://vitejs.dev/config/
export default defineConfig({
  base: '/static/',
  plugins: [svelte()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      // Proxy the FastAPI endpoints used by the app.
      '/humanize': API_HOST,
      '/methods': API_HOST,
      '/health': API_HOST,
      // Optional /api alias for future endpoints or local dev conventions.
      '/api': {
        target: API_HOST,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
