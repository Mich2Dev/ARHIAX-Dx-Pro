# Plan de Testing Exhaustivo — ARHIAX Dx

## 🎯 Objetivo
Probar todos los flujos del sistema end-to-end para identificar:
1. ✅ Lo que funciona correctamente
2. ❌ Lo que está roto
3. ⚠️ Lo que funciona parcialmente
4. 💡 Oportunidades de mejora

---

## 📋 Tests a Ejecutar

### 1. Backend — Motor de Gobernanza (back/)
- [ ] Healthcheck: `GET /healthz`
- [ ] Readiness: `GET /readyz`
- [ ] Compliance posture: `GET /v1/compliance/posture`
- [ ] Evaluate con mandato válido
- [ ] Evaluate con mandato inválido (sin size_org)
- [ ] Evaluate fuera de horario operativo
- [ ] Evaluate con herramienta no declarada
- [ ] Evaluate con patrón de inyección

### 2. Backend — Pipeline API (back-api/)
- [ ] Healthcheck: `GET /healthz`
- [ ] Auth: Register nuevo usuario
- [ ] Auth: Login con credenciales válidas
- [ ] Auth: Login con credenciales inválidas
- [ ] Diagnostics: Submit nuevo diagnóstico
- [ ] Diagnostics: List diagnósticos
- [ ] Diagnostics: Get detalle de diagnóstico
- [ ] Diagnostics: Stats
- [ ] Diagnostics: Download report (si hay completado)
- [ ] Reviews: Pending count
- [ ] Reviews: Pending list
- [ ] Reviews: Approve
- [ ] Reviews: Reject
- [ ] WebSocket: Stream de progreso

### 3. Frontend (front/)
- [ ] Login page
- [ ] Dashboard principal
- [ ] Wizard paso 1: Datos del cliente
- [ ] Wizard paso 2: Tipo de diagnóstico
- [ ] Wizard paso 3: Revisión y envío
- [ ] Submit diagnóstico
- [ ] Vista de diagnóstico en progreso
- [ ] Vista de diagnóstico completado
- [ ] Descarga de reporte DOCX
- [ ] Panel de revisiones
- [ ] Aprobar/rechazar revisión

### 4. Integración End-to-End
- [ ] Flujo completo: Crear diagnóstico → Ejecutar pipeline → Ver resultados → Descargar DOCX
- [ ] Flujo de revisión: Diagnóstico requiere aprobación → Revisor aprueba → Continúa
- [ ] Flujo de rechazo: Diagnóstico denegado por gobernanza

### 5. Tests Unitarios Existentes
- [ ] Ejecutar tests del motor de gobernanza
- [ ] Ejecutar tests del pipeline API (si existen)

---

## 🔍 Resultados del Testing

### ✅ Funciona Correctamente

### ❌ Está Roto

### ⚠️ Funciona Parcialmente

### 💡 Oportunidades de Mejora

---

## 📊 Métricas de Calidad
- Cobertura de tests: X%
- Endpoints funcionales: X/Y
- Flujos completos: X/Y
- Bugs críticos: X
- Bugs menores: X
