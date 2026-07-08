import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined;

          const normalizedId = id.replace(/\\/g, '/');
          if (
            normalizedId.includes('/react/') ||
            normalizedId.includes('/react-dom/') ||
            normalizedId.includes('/react-router-dom/')
          ) {
            return 'react-vendor';
          }
          if (
            normalizedId.includes('/antd/') ||
            normalizedId.includes('/@ant-design/') ||
            normalizedId.includes('/rc-') ||
            normalizedId.includes('/@rc-component/')
          ) {
            return 'antd-vendor';
          }
          if (
            normalizedId.includes('/axios/') ||
            normalizedId.includes('/dayjs/')
          ) {
            return 'utils';
          }

          return undefined;
        },
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
