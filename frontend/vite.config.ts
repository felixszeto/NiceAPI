import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://47.106.65.25:8001',
        changeOrigin: true
      },
      '/v1': {
        target: 'http://47.106.65.25:8001',
        changeOrigin: true
      }
    }
  }
})
