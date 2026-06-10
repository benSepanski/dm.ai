import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Bind on all interfaces so players on the same LAN can open the UI
    // from their own devices (http://<dm-laptop-ip>:5173).
    host: true,
    proxy: {
      // REST and WebSocket traffic both live under /api on the backend
      // (the WS route is /api/ws/sessions/...), so one proxy entry covers both.
      '/api': {
        target: process.env.VITE_API_URL ?? 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
