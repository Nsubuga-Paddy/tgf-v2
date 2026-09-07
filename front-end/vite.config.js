import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Django serves this folder as /static/frontend/... (under core/static).
const djangoFrontendDist = path.resolve(__dirname, '../core/static/frontend')

const apiProxy = {
  '/api': {
    target: process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000',
    changeOrigin: true,
    secure: false,
  },
}

export default defineConfig({
  plugins: [react()],
  // Empty / unset VITE_API_BASE_URL → browser calls /api on the same host (Django).
  base: process.env.VITE_DJANGO_BASE || '/static/frontend/',
  build: {
    outDir: process.env.VITE_DJANGO_OUT_DIR || djangoFrontendDist,
    emptyOutDir: true,
    assetsDir: 'assets',
    // Keep peak RAM lower on small Windows machines (Django static build).
    reportCompressedSize: false,
    sourcemap: false,
    rollupOptions: {
      maxParallelFileOps: 1,
    },
  },
  server: {
    host: '127.0.0.1',
    port: 4173,
    strictPort: false,
    open: false,
    proxy: apiProxy,
  },
  preview: {
    host: '127.0.0.1',
    port: 4173,
    proxy: apiProxy,
  },
})
