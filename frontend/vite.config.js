import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发时 /api 代理到后端, 前端代码直接用相对路径 /api/... 即可
export default defineConfig({
  plugins: [vue()],
  // Electron 环境下使用相对路径加载资源
  base: './',
  build: {
    outDir: '../electron/renderer',
    emptyOutDir: true,
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
