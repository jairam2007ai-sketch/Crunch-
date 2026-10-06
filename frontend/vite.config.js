import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

const here = (p) => fileURLToPath(new URL(p, import.meta.url))
const api = process.env.API_PROXY || 'http://127.0.0.1:8000'

// Three websites from one project: buyers at /, the seller POS at /seller/, the owner at /admin/.
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: { alias: { '@': here('./src') } },
  server: { port: 5173, proxy: { '/api': api } },
  preview: { port: 4173, proxy: { '/api': api } },
  build: {
    // three.js (~190 kB gzipped) loads only on buyer pages that show the 3D packet
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      input: {
        buyer: here('./index.html'),
        seller: here('./seller/index.html'),
        admin: here('./admin/index.html'),
      },
    },
  },
})
