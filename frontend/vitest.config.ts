/// <reference types="vitest" />
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      src: fileURLToPath(new URL('./src', import.meta.url)),
      boot: fileURLToPath(new URL('./src/boot', import.meta.url)),
      pages: fileURLToPath(new URL('./src/pages', import.meta.url)),
      components: fileURLToPath(new URL('./src/components', import.meta.url)),
      '#q-app/wrappers': fileURLToPath(new URL('./test-shims/q-app-wrappers.ts', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    css: true,
  },
})
