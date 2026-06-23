# ARHIAX Dx Pro Frontend Console

React + Vite operating console for ARHIAX Dx Pro.

This is not a public landing page. It is the first operational UI for running governed diagnostic cases, reviewing persisted case state, validating canonical grammar, approving or publishing cases and locating generated deliverables.

The user must enter directly into this DxPro experience. Do not expose a previous product selector between Dx, Dx Pro, Dx Agent or historical migration modules.

The visual system is inspired by `groupsinergia.com`: sober editorial typography, warm paper background, thin rules, restrained accents and a consulting dossier feel.

## Capabilities

- Run an end-to-end diagnostic case through `POST /v1/agents/cases/run`.
- Load persisted cases from `GET /v1/cases`.
- Inspect case status, approval status, trace ID and stage outcomes.
- Trigger approval workflow actions through `POST /v1/agents/cases/approval`.
- Publish through the explicit grammar-aware case publishing flow.
- Validate text against the ARHIAX canonical grammar panel.
- Display generated Markdown, DOCX and PDF deliverable paths.
- Use the Sinergia logo as owner brand with ARHIAX Dx Pro textual mark.

## Stack

- React 19
- TypeScript
- Vite
- Vitest
- CSS modules by convention through `App.css` and `index.css`

## Scripts

```powershell
npm install
npm run dev
npm run build
npm run lint
npm test
```

## Runtime Connection

Default local API base:

```text
http://127.0.0.1:8310
```

Override for staging or production:

```powershell
$env:VITE_DXPRO_API_URL = "https://api.dxpro.dominio.com"
npm run build
```

The backend must expose the case and grammar endpoints:

- `POST /v1/agents/cases/run`
- `POST /v1/agents/cases/approval`
- `POST /v1/cases/{case_id}/publish`
- `GET /v1/cases`
- `GET /v1/cases/{case_id}`
- `POST /v1/agents/grammar/lint`
- `GET /v1/cases/{case_id}/grammar`

## Source Map

| File | Purpose |
| --- | --- |
| `src/App.tsx` | Console workflow, API calls, sample case payload, case/approval/export views and grammar-gated publication. |
| `src/App.css` | Sinergia-inspired operating console design system. |
| `src/components/CanonicalGrammarPanel.tsx` | Canonical grammar UI panel. |
| `src/lib/canonicalGrammar.ts` | Frontend canonical grammar lint rules and publish decision helper. |
| `src/index.css` | Global font imports and baseline element rules. |
| `public/logo-sinergia.png` | Sinergia owner brand asset. |

## Current Limitations

- API-key authentication is not yet wired into the frontend request layer.
- Deliverables are shown as server-side paths; download endpoints or object storage are still a production hardening step.
- Case payload editing is currently JSON-first for operator flexibility.
- Responsive behavior is implemented, but final browser QA should be done before production release.

## Recommended Local Run

Terminal 1:

```powershell
cd ../..
python -m dxpro_runtime.server
```

Terminal 2:

```powershell
cd frontend/arhiax-dxpro-site
$env:VITE_DXPRO_API_URL = "http://127.0.0.1:8310"
npm run dev
```
