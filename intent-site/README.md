# `/intent` application

This directory contains the source for the Anticipatory Intelligence preview served at `https://mizoki3.com/intent` by the existing `mizoki-website` Cloud Run service.

The application is additive and path-scoped. It does not own the apex domain, DNS, a custom-domain mapping, a load-balancer rule, or any route outside `/intent`.

## Source layout

| Path | Purpose |
|---|---|
| `index.html` | SEO metadata, production canonical URL, and Vite entry point |
| `src/main.tsx` | React mount point |
| `src/Home.tsx` | Authored customer-facing page and interactions |
| `src/styles.css` | Route-local responsive design system |
| `vite.config.ts` | `/intent/` asset base and `../intent-dist` output contract |
| `tests/build.test.mjs` | Verifies the single canonical URL, route-scoped assets, preview-marker removal, and no root-favicon regression |
| `package.json` | Exact top-level frontend dependency versions and scripts |
| `package-lock.json` | Authoritative, reproducible npm dependency graph |

The generated `../intent-dist/` directory is a deployment artifact, not authored source. The deployment workflow creates it before Cloud Build packages the `# MIZ OKI 3.5/` container context.

## Dependency-install contract

Production uses Node.js 22.13.0 and the committed npm lockfile. Installation is fail-closed:

```bash
npm ci --no-audit --no-fund
npm test
npm audit --audit-level=high
```

There is no no-lock production fallback. If `package-lock.json` is absent or disagrees with `package.json`, `npm ci` must fail before an image is built.

When dependencies intentionally change, use Node.js 22.13.0 with its bundled npm 10.9.2 in an isolated copy:

```bash
npm install --package-lock-only --ignore-scripts --no-audit --no-fund
npm ci --no-audit --no-fund
npm test
npm audit --audit-level=high
```

Review and commit `package.json` and `package-lock.json` together. Do not regenerate the lockfile for unrelated changes.

Repository policy requires dependency installation and builds to run outside the Google Drive checkout. A safe local workflow is:

```bash
work_dir=$(mktemp -d)
cp -R "# MIZ OKI 3.5/intent-site" "$work_dir/intent-site"
cd "$work_dir/intent-site"

npm ci --no-audit --no-fund
npm test
npm audit --audit-level=high
```

`npm test` performs a production build and then checks the generated HTML. A successful build emits `intent-dist/index.html` plus hashed JavaScript and CSS under `intent-dist/assets/`.

## Build-repair note — 2026-08-22

Homepage deploy run `32587878059` passed human approval, design canon, content QA, and the marketing drift guard, then failed in setup-node before the build because the workflow declared an npm cache dependency path for a lockfile that had not yet been committed.

The path repair removed the root `/favicon.ico` import from Vite's build graph and added the build-contract regression test. The reproducibility follow-up then committed `package-lock.json`; successful production run `32602115967` used that same lockfile and reached the Vite build. The workflow now requires `npm ci` unconditionally.

The apex Flask site still owns its favicon; the `/intent` bundle does not need to compile it.

## Integration contracts

1. `vite.config.ts` must retain `base: "/intent/"`. Without it, generated assets resolve from the apex and can collide with the classic site.
2. Build output remains `../intent-dist`; Flask and the deployment workflow depend on that exact directory.
3. `index.html` keeps `https://mizoki3.com/intent` as its single canonical URL.
4. Do not add root-absolute build assets such as `/favicon.ico` to the Vite entry without a proven build-safe strategy. Existing site routes may still be linked root-absolutely from application content.
5. Authored public claims in `src/Home.tsx` are covered by `scripts/content_qa.py` and must retain required preview framing.
6. The page must not claim that intent inference has production execution authority. It is a preview and the displayed trace is illustrative.

## Runtime behavior

Flask serves the generated shell at `/intent` and `/intent/`. Files below `/intent/*` are resolved only from `intent-dist`; unknown generated paths return 404. The HTML shell uses `Cache-Control: no-cache`, while hashed files under `/intent/assets/` use one-year immutable caching.

For the end-to-end architecture, deployment ceremony, smoke tests, and rollback procedure, see [`../docs/INTENT_ROUTE_HOSTING.md`](../docs/INTENT_ROUTE_HOSTING.md).
