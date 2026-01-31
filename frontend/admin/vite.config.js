import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  // base 仅在生产构建时使用 /admin-panel/
  // 开发环境使用根路径，生产环境使用 /admin-panel/
  base: process.env.NODE_ENV === 'production' ? '/admin-panel/' : '/',
  plugins: [vue()],
  server: {
    port: 5174,
    proxy: {
      // 代理管理后台 API
      '/admin': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      // 代理其他 API(如果需要)
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})