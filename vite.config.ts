import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': '/src'
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes('/node_modules/plotly.js/') || id.includes('/node_modules/react-plotly.js/')) return 'plotly';
          if (id.includes('/node_modules/leaflet/') || id.includes('/node_modules/react-leaflet/')) return 'leaflet';
          if (id.includes('/node_modules/react/') || id.includes('/node_modules/react-dom/') || id.includes('/node_modules/react-router-dom/') || id.includes('/node_modules/framer-motion/')) return 'vendor';
        }
      }
    }
  }
})
