# 🚀 CHECKLIST PARA PRODUCCIÓN - ARHIAX Dx v5.1

## 📊 EVALUACIÓN GENERAL

| Categoría | Estado | Prioridad | Notas |
|-----------|--------|-----------|-------|
| **Seguridad** | ⚠️ CRÍTICO | 🔴 ALTA | Varios issues críticos |
| **Configuración** | ⚠️ MEJORAR | 🟡 MEDIA | Falta docker-compose.prod.yml |
| **Performance** | ✅ BUENO | 🟢 BAJA | Optimizado |
| **Monitoreo** | ❌ FALTA | 🔴 ALTA | Sin logging/metrics |
| **Backup** | ❌ FALTA | 🔴 ALTA | Sin estrategia de backup |
| **Documentación** | ✅ BUENO | 🟢 BAJA | Completa |

---

## 🔴 CRÍTICO - ARREGLAR ANTES DE PRODUCCIÓN

### 1. **Seguridad - Credenciales Hardcodeadas**

#### ❌ Problema:
```yaml
# docker-compose.yml
POSTGRES_PASSWORD: arhiax  # ← Hardcoded!
SECRET_KEY: arhiax-dx-dev-secret-change-in-prod  # ← Hardcoded!
```

#### ✅ Solución:
```bash
# Generar secrets fuertes
openssl rand -hex 32  # Para SECRET_KEY
openssl rand -base64 32  # Para POSTGRES_PASSWORD
```

**Acción requerida:**
- [ ] Cambiar todas las contraseñas hardcodeadas
- [ ] Usar variables de entorno desde .env
- [ ] Nunca commitear .env al repo

---

### 2. **Falta docker-compose.prod.yml**

#### ❌ Problema:
Solo existe `docker-compose.yml` para desarrollo.

#### ✅ Solución:
Crear `docker-compose.prod.yml` con:
- Secrets desde archivos externos
- Healthchecks más estrictos
- Restart policies adecuadas
- Límites de recursos (CPU/RAM)
- Networks aisladas
- Volúmenes para persistencia

**Acción requerida:**
- [ ] Crear docker-compose.prod.yml
- [ ] Configurar secrets de Docker
- [ ] Definir resource limits

---

### 3. **Sin Sistema de Logging**

#### ❌ Problema:
No hay logging centralizado ni rotación de logs.

#### ✅ Solución:
Opciones:
1. **ELK Stack** (Elasticsearch + Logstash + Kibana)
2. **Loki + Grafana** (más ligero)
3. **CloudWatch** (si usas AWS)
4. **Datadog** (SaaS)

**Acción requerida:**
- [ ] Implementar logging centralizado
- [ ] Configurar rotación de logs
- [ ] Definir niveles de log (INFO/WARNING/ERROR)

---

### 4. **Sin Monitoreo de Salud**

#### ❌ Problema:
No hay alertas ni dashboards de métricas.

#### ✅ Solución:
Implementar:
- **Prometheus** + **Grafana** para métricas
- **Alertmanager** para notificaciones
- Métricas clave:
  - CPU/RAM por servicio
  - Latencia de API
  - Tasa de errores
  - Queue depth (Redis)
  - DB connections

**Acción requerida:**
- [ ] Configurar Prometheus
- [ ] Crear dashboards en Grafana
- [ ] Definir alertas críticas

---

### 5. **Sin Estrategia de Backup**

#### ❌ Problema:
No hay backups automáticos de PostgreSQL.

#### ✅ Solución:
```bash
# Backup diario automático
0 2 * * * docker exec postgres pg_dump -U arhiax arhiax_dx | gzip > /backups/arhiax_$(date +\%Y\%m\%d).sql.gz

# Retención: 30 días
find /backups -name "arhiax_*.sql.gz" -mtime +30 -delete
```

**Acción requerida:**
- [ ] Configurar backups automáticos
- [ ] Definir política de retención
- [ ] Probar restauración de backups
- [ ] Backup de volúmenes Docker

---

## 🟡 IMPORTANTE - MEJORAR ANTES DE PRODUCCIÓN

### 6. **Variables de Entorno Expuestas**

#### ⚠️ Problema:
```yaml
# Todas las env vars están en docker-compose.yml
environment:
  GEMINI_API_KEY: ${GEMINI_API_KEY:-}  # ← Visible en logs
```

#### ✅ Solución:
Usar Docker secrets:
```yaml
secrets:
  gemini_api_key:
    file: ./secrets/gemini_api_key.txt
  
services:
  api:
    secrets:
      - gemini_api_key
```

**Acción requerida:**
- [ ] Migrar a Docker secrets
- [ ] Crear directorio secrets/ (en .gitignore)
- [ ] Documentar cómo generar secrets

---

### 7. **Sin Rate Limiting**

#### ⚠️ Problema:
API sin protección contra abuso.

#### ✅ Solución:
Implementar rate limiting en FastAPI:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/v2/diagnostics")
@limiter.limit("10/minute")  # Max 10 diagnósticos por minuto
async def create_diagnostic(...):
    ...
```

**Acción requerida:**
- [ ] Instalar slowapi
- [ ] Configurar límites por endpoint
- [ ] Documentar límites en API docs

---

### 8. **Sin HTTPS/SSL**

#### ⚠️ Problema:
Todo corre en HTTP sin encriptación.

#### ✅ Solución:
Usar **Nginx** o **Traefik** como reverse proxy con Let's Encrypt:
```yaml
services:
  traefik:
    image: traefik:v2.10
    command:
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@arhiax.com"
    ports:
      - "80:80"
      - "443:443"
```

**Acción requerida:**
- [ ] Configurar reverse proxy
- [ ] Obtener certificado SSL
- [ ] Forzar HTTPS redirect

---

### 9. **Sin CORS Configurado Correctamente**

#### ⚠️ Problema:
CORS puede estar muy permisivo o muy restrictivo.

#### ✅ Solución:
```python
# back-api/src/api/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://arhiax.com",
        "https://app.arhiax.com"
    ],  # ← Solo dominios específicos
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

**Acción requerida:**
- [ ] Revisar configuración CORS actual
- [ ] Restringir a dominios específicos
- [ ] Probar desde frontend en producción

---

### 10. **Sin Validación de Inputs Estricta**

#### ⚠️ Problema:
Posibles inyecciones SQL/XSS si no se valida bien.

#### ✅ Solución:
Ya usas Pydantic (✅), pero verificar:
- [ ] Todos los endpoints tienen schemas
- [ ] Validación de tamaños máximos
- [ ] Sanitización de HTML en inputs de texto
- [ ] Validación de emails/URLs

---

## 🟢 RECOMENDACIONES - MEJORAR DESPUÉS

### 11. **Optimización de Imágenes Docker**

```dockerfile
# Usar multi-stage builds (ya lo tienes ✅)
# Pero puedes optimizar más:

# Usar distroless para runtime
FROM gcr.io/distroless/python3-debian11
COPY --from=builder /app /app
CMD ["python", "-m", "api.main"]
```

---

### 12. **CI/CD Pipeline**

Configurar GitHub Actions / GitLab CI:
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build and push
        run: docker compose -f docker-compose.prod.yml build
      - name: Deploy
        run: ssh user@server "cd /app && docker compose pull && docker compose up -d"
```

---

### 13. **Documentación de Despliegue**

Crear `DEPLOYMENT.md` con:
- Requisitos del servidor (CPU/RAM/Disco)
- Pasos de instalación
- Configuración de DNS
- Troubleshooting común
- Procedimiento de rollback

---

### 14. **Testing en Staging**

Antes de producción:
- [ ] Crear entorno de staging idéntico
- [ ] Probar con datos reales (anonimizados)
- [ ] Load testing (Apache Bench, k6)
- [ ] Security testing (OWASP ZAP)

---

## 📋 CHECKLIST FINAL PRE-DEPLOY

### Seguridad
- [ ] Cambiar todas las contraseñas por defecto
- [ ] Generar SECRET_KEY único con openssl
- [ ] Configurar HTTPS/SSL
- [ ] Restringir CORS a dominios específicos
- [ ] Implementar rate limiting
- [ ] Migrar a Docker secrets
- [ ] Revisar permisos de archivos/carpetas

### Infraestructura
- [ ] Crear docker-compose.prod.yml
- [ ] Configurar resource limits
- [ ] Configurar restart policies
- [ ] Configurar healthchecks estrictos
- [ ] Configurar networks aisladas

### Monitoreo
- [ ] Implementar logging centralizado
- [ ] Configurar Prometheus + Grafana
- [ ] Definir alertas críticas
- [ ] Configurar notificaciones (email/Slack)

### Backup
- [ ] Configurar backups automáticos de PostgreSQL
- [ ] Configurar backups de volúmenes Docker
- [ ] Probar restauración de backups
- [ ] Documentar procedimiento de recuperación

### Performance
- [ ] Configurar Redis como cache
- [ ] Optimizar queries de DB (índices)
- [ ] Configurar CDN para assets estáticos
- [ ] Habilitar compresión gzip/brotli

### Documentación
- [ ] Crear DEPLOYMENT.md
- [ ] Documentar variables de entorno
- [ ] Documentar procedimientos de emergencia
- [ ] Crear runbook de operaciones

---

## 🎯 PRIORIDADES

### Semana 1 (CRÍTICO)
1. Cambiar credenciales hardcodeadas
2. Crear docker-compose.prod.yml
3. Configurar HTTPS/SSL
4. Implementar backups automáticos

### Semana 2 (IMPORTANTE)
5. Configurar logging centralizado
6. Implementar monitoreo (Prometheus/Grafana)
7. Configurar rate limiting
8. Migrar a Docker secrets

### Semana 3 (RECOMENDADO)
9. Testing en staging
10. Documentación de despliegue
11. CI/CD pipeline
12. Load testing

---

## 💰 COSTOS ESTIMADOS (AWS)

### Opción 1: EC2 (Self-managed)
- **t3.large** (2 vCPU, 8GB RAM): ~$60/mes
- **RDS PostgreSQL** (db.t3.small): ~$30/mes
- **ElastiCache Redis** (cache.t3.micro): ~$15/mes
- **ALB** (Load Balancer): ~$20/mes
- **Total**: ~$125/mes

### Opción 2: ECS Fargate (Serverless)
- **Fargate tasks** (0.5 vCPU, 1GB): ~$80/mes
- **RDS PostgreSQL**: ~$30/mes
- **ElastiCache Redis**: ~$15/mes
- **ALB**: ~$20/mes
- **Total**: ~$145/mes

### Opción 3: DigitalOcean (Más económico)
- **Droplet 4GB**: $24/mes
- **Managed PostgreSQL**: $15/mes
- **Managed Redis**: $15/mes
- **Load Balancer**: $12/mes
- **Total**: ~$66/mes

---

## 🚨 RIESGOS ACTUALES

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Credenciales expuestas | Alta | Crítico | Cambiar inmediatamente |
| Sin backups | Media | Crítico | Configurar backups diarios |
| Sin monitoreo | Alta | Alto | Implementar Prometheus |
| Sin HTTPS | Alta | Alto | Configurar SSL |
| Sin rate limiting | Media | Medio | Implementar slowapi |

---

## ✅ CONCLUSIÓN

**Estado actual**: ⚠️ **NO LISTO PARA PRODUCCIÓN**

**Razones**:
1. 🔴 Credenciales hardcodeadas
2. 🔴 Sin backups
3. 🔴 Sin monitoreo
4. 🟡 Sin HTTPS
5. 🟡 Sin logging centralizado

**Tiempo estimado para estar listo**: **2-3 semanas**

**Recomendación**: Implementar los items críticos (Semana 1) antes de cualquier deploy a producción.
