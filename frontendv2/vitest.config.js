import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vitest reads THIS file in preference to vite.config.js and does not merge the
// two, so the react plugin has to be repeated here or every .jsx test fails to
// transform. Keep the plugin list in sync with vite.config.js.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.js'],
    include: ['src/**/*.test.{js,jsx}'],
    css: false,
    restoreMocks: true,
    clearMocks: true,
  },
});
