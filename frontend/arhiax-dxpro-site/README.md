# ARHIAX Dx Pro Frontend Console

Consola operativa React + Vite para ARHIAX Dx Pro.

Esta interfaz no es una landing pública. Es la experiencia de trabajo para ejecutar casos, revisar expediente, validar textos, aprobar o publicar resultados y ubicar entregables generados.

El usuario debe entrar directamente a Dx Pro. No debe aparecer una selección previa entre Dx, Dx Pro, Dx Agent u otros módulos históricos.

## Scripts

```powershell
npm install
npm run dev
npm run build
npm run lint
npm test
```

## Conexión con Runtime

API local por defecto:

```text
http://127.0.0.1:8310
```

Para staging o producción:

```powershell
$env:VITE_DXPRO_API_URL = "https://api.dxpro.dominio.com"
npm run build
```

## Endpoints Usados

- `GET /v1/cases`
- `GET /v1/cases/{case_id}`
- `POST /v1/agents/cases/run`
- `POST /v1/agents/cases/approval`
- `POST /v1/cases/{case_id}/publish`
- `POST /v1/agents/grammar/lint`
- `GET /v1/cases/{case_id}/grammar`

## Estructura

- `src/App.tsx`: composición principal de la consola.
- `src/components/`: paneles de aprobación, expediente, gramática y confirmación.
- `src/hooks/`: carga de casos y ejecución de diagnóstico.
- `src/lib/apiRequest.ts`: cliente HTTP del frontend.
- `src/lib/types.ts`: tipos compartidos de la UI.
- `src/App.css`: sistema visual de la consola.
- `public/logo-sinergia.png`: marca propietaria de Sinergia.

## Limitaciones Pendientes

- La API key todavía no está conectada desde la capa de frontend.
- Los entregables se muestran como rutas del servidor; falta definir descarga autenticada u object storage.
- El payload del caso sigue siendo JSON-first para flexibilidad operativa.
