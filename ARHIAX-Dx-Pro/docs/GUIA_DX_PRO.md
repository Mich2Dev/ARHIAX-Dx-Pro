# Guía de Uso: ARHIAX Dx Pro

## ¿Qué es Dx Pro?

Dx Pro es un **runtime avanzado completamente independiente** con:
- **Fusion Cycle**: Ciclo diagnóstico inteligente con síntesis Bayesiana
- **PMEL/ATK Governance**: Gobernanza de políticas con OPA
- **Evidence Ledger HMAC**: Registro de evidencia inmutable
- **Workflow de Aprobación**: Control humano (HIL) para casos
- **Exportación Multi-formato**: Markdown, DOCX, PDF

## Diferencias con Dx Standard

| Característica | Dx Standard | Dx Pro |
|---|---|---|
| **Usuarios** | Clientes finales | Operadores técnicos |
| **Interfaz** | Amigable, guiada | Técnica, JSON directo |
| **Agentes** | 18 especializados | Fusion cycle unificado |
| **Encuestas** | Multi-rater completo | Matriz de respuestas |
| **Gobernanza** | OPA básico | PMEL/ATK completo |
| **Evidencia** | Logs | HMAC ledger |
| **Aprobación** | Revisión simple | Workflow HIL |
| **Dependencias** | PostgreSQL, Redis | Standalone |

## Acceso a Dx Pro

### 1. Login
- Ir a: `http://localhost:3000/login`
- Seleccionar **"Dx Pro"**
- Credenciales: `admin@sinergia.co` / `test1234`
- Redirige a: `/dashboard-pro`

### 2. Dashboard Pro

El dashboard tiene 6 secciones principales:

#### A. Ejecutar Ciclo Gobernado
- **Input JSON**: Editor de payload del caso
- **Botón "Ejecutar caso"**: Inicia el fusion cycle
- **Botón "Restaurar muestra"**: Carga payload de ejemplo

#### B. Expediente
Muestra información del caso activo:
- Cliente y dominio
- Estado del caso
- Estado de aprobación
- Trace ID (para auditoría)
- Etapas del ciclo: fusion → report → render → export

#### C. Casos Persistidos
- Lista de todos los casos ejecutados
- Click para ver detalles
- Icono verde = completado
- Icono amarillo = en proceso

#### D. Control Humano (HIL)
Workflow de aprobación:
- **Aprobar**: Marca el caso como aprobado
- **Publicar**: Publica el caso para entrega
- **Rechazar**: Rechaza el caso

#### E. Entregables
Lista de archivos exportados:
- Markdown (.md)
- DOCX (.docx)
- PDF (.pdf)
- Muestra ruta y tamaño

## Flujo de Trabajo

### Opción 1: Ejecutar Caso Directo en Pro

```
1. Login → Seleccionar "Dx Pro"
2. Dashboard Pro → Editar JSON del caso
3. Click "Ejecutar caso"
4. Esperar que complete las 4 etapas
5. Revisar entregables
6. Aprobar/Publicar/Rechazar
```

### Opción 2: Desde Standard con Botón Pro

```
1. Login → Seleccionar "Dx Standard"
2. Crear diagnóstico normal
3. Esperar respuestas de encuesta
4. Click botón "Pro ⚡" en detalle
5. Ver resultado en Dashboard Pro
```

## Estructura del Payload JSON

```json
{
  "consent": {
    "action": "ingest_to_llm",
    "consents": { "T1": true, "T3": true }
  },
  "engagement_id": "eng-unique-id",
  "client": {
    "legal_name": "Nombre de la Organización"
  },
  "domain": "sector o dominio del diagnóstico",
  "roles": ["executive", "operations", "technology"],
  "dimensions": ["strategy", "process", "technology"],
  "responses": [
    {
      "role": "executive",
      "dimension": "strategy",
      "item_id": "strategy-1",
      "score": 4
    }
    // ... más respuestas
  ],
  "response_matrix": [
    [4, 3, 3],
    [2, 2, 2],
    [3, 4, 4]
  ],
  "diagnostic_hypotheses": [
    {
      "id": "DH1",
      "statement": "Hipótesis diagnóstica",
      "prior": 0.55
    }
  ],
  "evidence_signals": [
    {
      "id": "sig-1",
      "hypothesis_ids": ["DH1"],
      "likelihood_ratio": 1.6
    }
  ],
  "hypothesis_pack": {
    "hypothesis_pack_version": "1.0",
    "engagement_id": "eng-unique-id",
    "domain": "sector",
    "hypotheses": [
      {
        "id": "H1",
        "statement": "Hipótesis de mejora"
      }
    ]
  },
  "grey_sources": [
    {
      "id": "grey-1",
      "title": "Fuente",
      "content": "Contenido de referencia"
    }
  ],
  "bpmn_model": {
    "nodes": [
      { "id": "start", "type": "start_event", "name": "Inicio" },
      { "id": "t1", "type": "task", "name": "Tarea" },
      { "id": "end", "type": "end_event", "name": "Fin" }
    ],
    "edges": [
      { "source": "start", "target": "t1" },
      { "source": "t1", "target": "end" }
    ]
  },
  "targets": ["markdown", "docx", "pdf"]
}
```

## Estados del Caso

### Case Status
- `pending`: Caso creado, esperando ejecución
- `running`: Ejecutando fusion cycle
- `completed`: Ciclo completado exitosamente
- `failed`: Error en ejecución

### Approval Status
- `draft`: Borrador, no revisado
- `pending_approval`: Esperando aprobación
- `approved`: Aprobado por revisor
- `published`: Publicado para entrega
- `rejected`: Rechazado

## Etapas del Fusion Cycle

1. **Fusion**: Síntesis diagnóstica con Bayesian reasoning
2. **Report**: Generación de reporte ejecutivo
3. **Render**: Renderizado a formato UTF-8
4. **Export**: Exportación a Markdown/DOCX/PDF

Cada etapa retorna:
- `PERMIT`: Aprobada por gobernanza
- `DENY`: Denegada
- `ESCALATE`: Requiere revisión humana
- `SUSPEND`: Suspendida

## API Endpoints de Dx Pro

### Casos
- `GET /v1/cases` - Listar casos
- `GET /v1/cases/{case_id}` - Obtener caso
- `POST /v1/agents/cases/run` - Ejecutar caso
- `POST /v1/agents/cases/approval` - Aprobar/rechazar

### Gobernanza
- `GET /v1/compliance/posture` - Estado de gobernanza
- `POST /v1/pmel/evaluate` - Evaluar política
- `POST /v1/pmel/run-step` - Ejecutar cadena de políticas

### Evidencia
- `GET /v1/evidence` - Entradas recientes
- `GET /v1/evidence/verify` - Verificar cadena HMAC
- `GET /v1/audit-pack/{trace_id}` - Paquete de auditoría

### Health
- `GET /healthz` - Health check
- `GET /readyz` - Readiness check

## Servicios Docker

```bash
# Ver servicios activos
docker ps

# Dx Pro corre en puerto 8310
http://localhost:8310

# Frontend en puerto 3000
http://localhost:3000
```

## Troubleshooting

### "No se pudo conectar con DxPro Runtime"
- Verificar que el servicio esté corriendo: `docker ps | grep dxpro`
- Verificar health: `http://localhost:8310/healthz`
- Reiniciar: `docker compose restart dxpro`

### "El JSON del caso no es válido"
- Verificar sintaxis JSON
- Usar botón "Restaurar muestra" para payload válido
- Verificar que todos los campos requeridos estén presentes

### "No hay casos ejecutados aún"
- Ejecutar un caso usando el botón "Ejecutar caso"
- O ejecutar desde Standard con botón "Pro ⚡"
- Verificar que el servicio Dx Pro esté corriendo

### Caso no aparece en la lista
- Click en botón de actualizar (↻)
- Verificar que la ejecución haya completado
- Revisar logs: `docker logs arhiax-dx-agent-main-dxpro-1`

## Notas Importantes

1. **Dx Pro es para operadores técnicos**, no usuarios finales
2. **Requiere conocimiento de JSON** y estructura de datos
3. **No tiene wizard guiado** como Standard
4. **Es completamente independiente** de Standard
5. **Los casos se persisten localmente** en `data/cases/`
6. **Los exports se guardan en** `data/exports/`
7. **El ledger HMAC está en** `data/evidence.jsonl`

## Próximos Pasos

- [ ] Configurar autenticación con API keys
- [ ] Implementar descarga de entregables desde UI
- [ ] Agregar visualización de trace evidence
- [ ] Integrar con object storage para exports
- [ ] Agregar logs y observabilidad
- [ ] Configurar backup de casos y evidencia
