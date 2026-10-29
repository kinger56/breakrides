import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // In development, Vite serves the page on :5173 and forwards /api calls
    // to FastAPI on :8000. The browser sees one origin, so the login
    // cookie works exactly like it will in production.
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
