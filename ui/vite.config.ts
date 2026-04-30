import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/chat': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/cancel': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/status': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/approve': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/settings': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/voice': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/music': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/canvas': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/session': {
        target: 'http://localhost:9200',
        changeOrigin: true,
      },
      '/profile': {
        target: 'http://localhost:9200',
        changeOrigin: true,
      },
      '/ingest': {
        target: 'http://localhost:9200',
        changeOrigin: true,
      },
      '/kb': {
        target: 'http://localhost:9200',
        changeOrigin: true,
      },
      '/navidrome': {
        target: 'http://localhost:4533',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/navidrome/, ''),
      },
    },
  },
})
