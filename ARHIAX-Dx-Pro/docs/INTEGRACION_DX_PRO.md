# 🔗 Integración Dx Standard + Dx Pro

## 📊 Arquitectura Integrada

```
┌─────────────────────────────────────────────────┐
│           FRONTEND (Puerto 3000)                │
│  ┌──────────────────────────────────────────┐  │
│  │  Dashboard con selector de motor:        │  │
│  │  • Botón "Ver resultados" (Standard)     │  │
│  │  • Botón "Pro ⚡" (Dx Pro)               │  │
│  │  • Botón "PDF" (Descarga)                │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│         BACKEND API (Puerto 8000)               │
│  ┌──────────────────────────────────────────┐  │
│  │  Endpoints:                              │  │
│  │  • POST /v2/diagnostics (Standard)       │  │
│  │  • POST /v2/diagnostics/{id}/execute-pro│  │
│  └──────────────────────────────────────────┘  │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Datos Compartidos:                      │  │
│  │  • PostgreSQL (diagnósticos, encuestas)  │  │
│  │  • Redis (cache, queue)                  │  │
│  │  • Usuarios y autenticación              │  │
│  └──────────────────────────────────────────┘  │
│           │                    │                │
│           ▼                    ▼                │
│  ┌──────────────┐    ┌──────────────────────┐ │
│  │ Motor        │    │ Adaptador Dx Pro     │ │
│  │ Standard     │    │ (dxpro_adapter.py)   │ │
│  │ (18 agentes) │    └──────────┬───────────┘ │
│  └──────────────┘               │              │
└─────────────────────────────────┼──────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │  DX PRO (Puerto 8310)       │
                    │  • Fusion cycle             │
                    │  • PMEL/ATK governance      │
                    │  • Evidence HMAC            │
                    └─────────────────────────────┘
```

## 🎯 Flujo de Usuario

### Opción 1: Motor Standard (Original)
1. Usuario crea diagnóstico → Wizard
2. Sistema envía encuestas
3. Espera 5+ respuestas
4. Click "Ver resultados" → Ejecuta 18 agentes
5. Genera PDF/DOCX

### Opción 2: Motor Pro (Nuevo)
1. Usuario crea diagnóstico → Wizard (MISMO)
2. Sistema envía encuestas (MISMO)
3. Espera 5+ respuestas (MISMO)
4. Click "Pro ⚡" → Ejecuta fusion cycle
5. Genera PDF/DOCX (MISMO)

## 🔧 Componentes Técnicos

### Backend

**Adaptador (`dxpro_adapter.py`):**
```python
class DxProAdapter:
    def convert_diagnostic_to_pro_format(diagnostic, responses):
        # Convierte de PostgreSQL a formato Pro
        
    def execute_diagnostic(diagnostic, responses):
        # Llama a Dx Pro API
```

**Router (`routers/dxpro.py`):**
```python
@router.post("/v2/diagnostics/{id}/execute-pro")
async def execute_with_pro_engine(id):
    # 1. Obtener datos de PostgreSQL
    # 2. Convertir a formato Pro
    # 3. Llamar a Dx Pro
    # 4. Guardar resultados
```

### Frontend

**Componente (`ExecuteProButton.tsx`):**
```tsx
<button onClick={() => api.post(`/v2/diagnostics/${id}/execute-pro`)}>
  <Zap /> Pro
</button>
```

## 📦 Servicios Docker

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **postgres** | 5434 | Base de datos compartida |
| **redis** | 6380 | Cache compartido |
| **governance** | 8088 | Gobernanza OPA |
| **api** | 8000 | Backend Standard + adaptador Pro |
| **worker** | - | Worker Celery |
| **dxpro** | 8310 | Motor Dx Pro |
| **frontend** | 3000 | Next.js |

## 🚀 Inicio Rápido

```bash
# 1. Configurar variables
cp .env.example .env
# Editar .env y agregar:
#   GEMINI_API_KEY=...
#   ANTHROPIC_API_KEY=...

# 2. Iniciar todo
start-integrated.bat

# O manualmente:
docker compose up --build
```

## 🔑 Variables de Entorno

```env
# LLM Providers
GEMINI_API_KEY=tu-key-aqui
ANTHROPIC_API_KEY=tu-key-aqui

# Dx Pro Integration
DXPRO_URL=http://dxpro:8310
```

## ✅ Verificación

### 1. Verificar servicios
```bash
docker compose ps
```

Todos deben estar "healthy".

### 2. Verificar API
```bash
curl http://localhost:8000/healthz
curl http://localhost:8310/healthz
```

### 3. Verificar frontend
Abrir http://localhost:3000

### 4. Probar integración
1. Login con admin@sinergia.co / test1234
2. Crear diagnóstico
3. Esperar 5+ respuestas de encuesta
4. Click botón "Pro ⚡"
5. Verificar ejecución exitosa

## 🐛 Troubleshooting

### Error: "No se pudo conectar con DxPro"
```bash
# Verificar que dxpro está corriendo
docker compose logs dxpro

# Reiniciar servicio
docker compose restart dxpro
```

### Error: "Se requieren al menos 5 respuestas"
El diagnóstico necesita mínimo 5 respuestas de encuesta antes de ejecutar.

### Error: "ANTHROPIC_API_KEY no configurada"
Dx Pro requiere Anthropic API key. Agregar en `.env`:
```env
ANTHROPIC_API_KEY=sk-ant-...
```

## 📊 Comparación de Motores

| Aspecto | Standard | Pro |
|---------|----------|-----|
| **Velocidad** | Lento (secuencial) | Rápido (fusionado) |
| **Agentes** | 18 separados | Fusion cycle |
| **Gobernanza** | OPA básica | PMEL/ATK avanzada |
| **Evidence** | Simple | HMAC encadenado |
| **Tests** | Pocos | 92 tests |
| **Dependencias** | PostgreSQL + Redis | Solo archivos |

## 🎓 Notas Técnicas

### ¿Por qué 2 motores?

- **Standard**: Probado, estable, completo
- **Pro**: Más rápido, más potente, más tests

### ¿Cuándo usar cada uno?

- **Standard**: Diagnósticos normales, producción estable
- **Pro**: Diagnósticos complejos, necesitas velocidad

### ¿Se pueden usar ambos?

Sí, el usuario elige en el dashboard cuál usar.

### ¿Comparten datos?

Sí, ambos usan la misma PostgreSQL, Redis, encuestas, usuarios.

## 📚 Archivos Clave

```
/
├── back-api/src/api/
│   ├── services/dxpro_adapter.py    # Adaptador
│   └── routers/dxpro.py             # Endpoint
├── front/src/components/features/diagnostics/
│   └── ExecuteProButton.tsx         # Botón UI
├── ARHIAX-Dx-Pro/                   # Motor Pro
├── docker-compose.yml               # Orquestación
└── start-integrated.bat             # Script inicio
```

## 🔄 Flujo de Datos

```
Usuario → Frontend → API → Adaptador → Dx Pro
                      ↓
                 PostgreSQL (guarda resultado)
```

## ✨ Beneficios de la Integración

1. ✅ **Flexibilidad**: Usuario elige motor
2. ✅ **Sin duplicación**: Datos compartidos
3. ✅ **Mejor de ambos**: Standard estable + Pro potente
4. ✅ **Fácil migración**: Cambiar de motor sin perder datos
5. ✅ **Testing**: Pro tiene 92 tests automatizados

---

**Versión:** Dx v5.1 + Pro v1.0 Integrado  
**Fecha:** Abril 2026
