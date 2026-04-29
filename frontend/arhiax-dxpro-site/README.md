# ARHIAX DxPro Frontend Console

React + Vite operating console for ARHIAX DxPro.

This is not a public landing page. It is the first operational UI for running governed diagnostic cases, reviewing persisted case state, approving or publishing cases and locating generated deliverables.

The visual system is inspired by `groupsinergia.com`: sober editorial typography, warm paper background, thin rules, restrained accents and a consulting dossier feel.

## Capabilities

- Run an end-to-end diagnostic case through `POST /v1/agents/cases/run`.
- Load persisted cases from `GET /v1/cases`.
- Inspect case status, approval status, trace ID and stage outcomes.
- Trigger approval workflow actions through `POST /v1/agents/cases/approval`.
- Display generated Markdown, DOCX and PDF deliverable paths.
- Use the Sinergia logo as owner brand with provisional ARHIAX DxPro textual mark.

## Stack

- React 19
- TypeScript
- Vite
- CSS modules by convention through `App.css` and `index.css`

## Scripts

```powershell
npm install
npm run dev
npm run build
npm run lint
```

## Runtime Connection

Default API base:

```text
http://127.0.0.1:8000
```

Override with:

```powershell
$env:VITE_DXPRO_API_URL = "http://127.0.0.1:8310"
npm run dev
```

The backend must expose the case endpoints:

- `POST /v1/agents/cases/run`
- `POST /v1/agents/cases/approval`
- `GET /v1/cases`
- `GET /v1/cases/{case_id}`

## Source Map

| File | Purpose |
| --- | --- |
| `src/App.tsx` | Console workflow, API calls, sample case payload and case/approval/export views. |
| `src/App.css` | Sinergia-inspired operating console design system. |
| `src/index.css` | Global font imports and baseline element rules. |
| `public/logo-sinergia.png` | Sinergia owner brand asset. |

## Current Limitations

- API-key authentication is not yet wired into the frontend request layer.
- Deliverables are shown as server-side paths; download endpoints/object storage are still a production hardening step.
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
