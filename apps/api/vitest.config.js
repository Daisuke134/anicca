import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['src/**/__tests__/**/*.test.js', 'src/**/*.test.js'],
    setupFiles: ['./src/test/setup.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/services/ops/**', 'src/middleware/**', 'src/routes/ops/**', 'src/routes/agent/**', 'src/lib/**'],
    },
  },
});
