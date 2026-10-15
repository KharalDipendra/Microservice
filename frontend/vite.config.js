import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    // Every /api/* request from the browser goes to the nginx API gateway,
    // which routes it to the right microservice. The browser never needs to
    // know individual service ports, and there are no CORS issues.
    proxy: {
      '/api': { target: 'http://gateway:80', changeOrigin: true }
    }
  }
})
