import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

function normalizeBasePath(value = '/') {
  const segments = String(value).trim().split('/').filter(Boolean)
  return segments.length ? `/${segments.join('/')}/` : '/'
}

const base = normalizeBasePath(process.env.VITE_BASE_PATH)
const basePrefix = base === '/' ? '' : base.slice(0, -1)

function backendPreviewProxy(path) {
  return {
    target: 'http://localhost:8000',
    changeOrigin: true,
    ws: path === 'socket.io',
    rewrite: (requestPath) => (
      basePrefix && requestPath.startsWith(basePrefix)
        ? requestPath.slice(basePrefix.length) || '/'
        : requestPath
    ),
  }
}

const previewProxy = Object.fromEntries(
  ['socket.io', 'media', 'intro'].map((path) => [
    `${basePrefix}/${path}`,
    backendPreviewProxy(path),
  ]),
)

// https://vitejs.dev/config/
export default defineConfig({
  base,
  plugins: [react()],
  server: {
    host: true, // Позволяет слушать на 0.0.0.0 (нужно для Docker)
    port: 5173
  },
  preview: {
    host: true,
    port: 4173,
    strictPort: true,
    proxy: previewProxy,
  }
})

