import { defineConfig } from 'vite';

/**
 * Vite configuration for the embeddable Cero widget IIFE bundle.
 *
 * This config is separate from the main app build so the existing app
 * behavior, output directory, and dev proxy stay untouched.
 */
export default defineConfig({
  build: {
    outDir: 'dist-widget',
    emptyOutDir: true,
    lib: {
      entry: 'src/widget.ts',
      name: 'CeroWidget',
      formats: ['iife'],
      fileName: 'cero-widget',
    },
  },
});
