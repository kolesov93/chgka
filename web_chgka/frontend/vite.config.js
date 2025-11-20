import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Позволяет слушать на 0.0.0.0 (нужно для Docker)
    port: 5173
  }
})


