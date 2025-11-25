import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/fileshare': {
        target: 'http://fileshare:5000',
        changeOrigin: true
      }
    }
  }
})
