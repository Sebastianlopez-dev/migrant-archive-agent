# Plataforma Cero index demo snapshot

This directory contains a local copy of the Plataforma Cero index page used only to test the embeddable Cero chat widget inside the migrant-archive repository.

It is **not** the source of truth for the Plataforma website. Copied image assets and local paths are rewritten so the page renders offline. External links, embedded videos, and forms continue to point to their original third-party services.

## Running the demo

The demo loads the widget from `frontend/dist-widget/cero-widget.iife.js`, which is a generated artifact and is ignored by git.

1. Start the backend at `http://localhost:8000`.
2. From the `frontend` directory, build the widget:
   ```bash
   pnpm run build:widget
   ```
3. Start the Vite dev server:
   ```bash
   pnpm dev
   ```
4. Open `http://localhost:5173/index-demo/` (or the equivalent dev-server URL).

The widget will connect to `http://localhost:8000` via the `api-base-url` attribute configured in `index.html`.
