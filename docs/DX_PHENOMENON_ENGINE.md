# Dx Phenomenon Engine v1

Motor de abordaje estilo Governex/Ray: **fenómeno → epoqué → convergencia → contradicción → localización → kill critic → derivación de documentos**.

## Fases

| Fase | ID | LLM | Salida principal |
|------|-----|-----|------------------|
| Recepción | `p01_reception` | No (código) | Material bruto normalizado |
| Epoqué | `p02_epoche` | Sí | Diagnósticos falsos del cliente refutados |
| Convergencia | `p03_convergence` | Sí | Fenómeno nombrado + hallazgos por lente |
| Contradicción | `p04_contradiction` | Sí | Contradicción técnica/física + motor |
| Localización | `p05_localization` | Sí | Subsistemas, acoplamientos rotos, pregunta bisagra |
| Kill Critic | `p06_kill_critic` | Sí | Riesgos, pruebas, `gates_passed` |
| Derivación | `p07_derivation` | Sí | Documentos recomendados + siguiente paso |

## Persistencia

`input_payload.phenomenon_analysis`:

```json
{
  "version": "1.0",
  "status": "running|completed|failed",
  "stages": [],
  "p01_reception": {},
  "p02_epoche": {},
  "p03_convergence": {},
  "p04_contradiction": {},
  "p05_localization": {},
  "p06_kill_critic": {},
  "p07_derivation": {},
  "summary": {
    "phenomenon_named": "",
    "resolution_motor": "",
    "gates_passed": true,
    "recommended_documents": []
  }
}
```

## API

`POST /pro/cases/{id}/analyze` — ejecuta P01–P07 en background.

`GET /pro/cases/{id}/download/phenomenon-internal` — análisis interno (.md).

`GET /pro/cases/{id}/download/phenomenon-discovery` — formulario de descubrimiento (.md).

## Gates (fail-closed comercial)

Si `p06_kill_critic.gates_passed === false`, el caso puede seguir pero **no debe generar propuesta comercial** hasta resolver pruebas bloqueantes.

## Tipos de documento (catálogo P07)

- `internal_phenomenon` — análisis interno (7 puntas)
- `discovery_form` — formulario de descubrimiento
- `commercial_proposal` — propuesta comercial
- `horizon_map` — mapa de fases
- `executive_report` — informe ejecutivo (PDF actual)
- `seed_data_template` — plantilla Excel/CSV
- `survey_instrument` — encuesta G09

## Relación con G01–G14

G01–G14 corren **después** de fenómeno nombrado (futuro). Hoy el análisis de fenómeno es independiente del pipeline legacy.
