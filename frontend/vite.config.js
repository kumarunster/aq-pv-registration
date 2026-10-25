import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { writeFileSync, mkdirSync } from 'fs'
import { join } from 'path'

// Build-Zeit erzeugen und in src/build-time.ts schreiben
const BUILD_TIME = new Date().toISOString()
const outDir = join(process.cwd(), 'src')
mkdirSync(outDir, { recursive: true })
writeFileSync(join(outDir, 'build-time.ts'), `export const BUILD_TIME = ${JSON.stringify(BUILD_TIME)}\n`)

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173
  }
})
