import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  base: '/dashboard/',
  build: {
    outDir: path.resolve(__dirname, '../src/insureflow/static/ui'),
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8002',
      '/auth': 'http://127.0.0.1:8002',
      '/pipeline': 'http://127.0.0.1:8002',
      '/mortgage': 'http://127.0.0.1:8002',
      '/system': 'http://127.0.0.1:8002',
    },
  },
});
