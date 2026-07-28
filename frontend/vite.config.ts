import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // One `.env` for the whole project (.env.example, runbook.md) rather than a second,
  // frontend-only copy — Vite looks here instead of its own root for VITE_-prefixed vars.
  envDir: '..',
})
