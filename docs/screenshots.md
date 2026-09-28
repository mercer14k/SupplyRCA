# Screenshot capture

Committed screenshots are from the actual app with the synthetic dataset, not design mockups. Desktop: `docs/screenshots/workspace.png`; mobile: `docs/screenshots/mobile.png`.

Start API + Vite using README, install Playwright Chromium, then:

```sh
cd apps/web
CAPTURE_SCREENSHOTS=1 pnpm test:e2e
```

PowerShell: `$env:CAPTURE_SCREENSHOTS='1'; pnpm test:e2e`. Set `E2E_BASE_URL=http://localhost:8080` for Compose. Optional `PLAYWRIGHT_CHROMIUM_EXECUTABLE` can point to an existing compatible Chromium executable.

The browser test waits for actual supplier-shortfall findings, captures the workspace at 1440×1050, then exercises evidence, review, persistence and report export. A second test checks a 390×844 viewport and captures the mobile view. Full-page PNGs are saved, and page-level horizontal overflow is checked. All displayed values originate from the API. Analyst disposition in a screenshot may reflect earlier saved review events.
