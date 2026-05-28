# 📁 Estructura del Proyecto ARHIAX Dx v5.1

## 🌳 Árbol de Directorios

```
ARHIAX-Dx-Agent/
│
├── 📂 back/                          # Governance Service (Puerto 8088)
│   ├── docs/                         # Documentación técnica
│   │   ├── ARCHITECTURE.md           # Arquitectura del sistema
│   │   ├── THREAT_MODEL.md           # Modelo de amenazas
│   │   └── audit-pack/               # Paquete de auditoría
│   ├── policies/                     # Políticas OPA
│   │   └── bundles/                  # Bundles de gobernanza
│   ├── specs/                        # Especificaciones JSON
│   │   ├── agent_identity.json       # Identidad del agente
│   │   ├── tool_catalog.json         # Catálogo de herramientas
│   │   └── policy_matrix.json        # Matriz de políticas
│   ├── src/arhiax_dx/                # Código fuente
│   │   ├── services/                 # Servicios de gobernanza
│   │   │   ├── governance.py         # Motor de gobernanza
│   │   │   ├── evidence.py           # Evidence ledger
│   │   │   └── provenance.py         # Firma de certificados
│   │   ├── main.py                   # FastAPI app
│   │   └── config.py                 # Configuración
│   ├── tests/                        # Tests unitarios
│   ├── var/                          # Datos runtime
│   │   └── evidence-ledger.jsonl     # Ledger de auditoría
│   ├── Dockerfile                    # Docker image
│   ├── pyproject.toml                # Dependencias Python
│   └── .env                          # Variables de entorno
│
├── 📂 back-api/                      # Pipeline API (Puerto 8000)
│   ├── alembic/                      # Migraciones de DB
│   │   └── versions/                 # Versiones de schema
│   ├── docs-project/                 # Documentación del proyecto
│   │   ├── PLATAFORMA.md             # Descripción de plataforma
│   │   ├── ESTADO_ACTUAL_Y_PIPELINE.md
│   │   └── COMO_FUNCIONAN_LAS_ENCUESTAS.md
│   ├── scripts/                      # Scripts de utilidad
│   │   ├── check_db.py               # Verificar DB
│   │   └── inspect_diagnostic.py     # Inspeccionar diagnóstico
│   ├── src/api/                      # Código fuente
│   │   ├── routers/                  # Endpoints REST
│   │   │   ├── diagnostics.py        # CRUD diagnósticos
│   │   │   ├── survey.py             # API de encuestas
│   │   │   ├── reviews.py            # Revisiones humanas
│   │   │   └── auth.py               # Autenticación
│   │   ├── pipeline/                 # Pipeline de 18 agentes
│   │   │   ├── executor.py           # Ejecutor de agentes
│   │   │   ├── prompts/              # Prompts de cada agente
│   │   │   ├── pdf_builder.py        # Generador PDF
│   │   │   └── docx_builder.py       # Generador DOCX
│   │   ├── models.py                 # ORM SQLAlchemy
│   │   ├── main.py                   # FastAPI app
│   │   ├── worker.py                 # Worker asíncrono
│   │   ├── pipeline_runner.py        # Orquestador pipeline
│   │   └── config.py                 # Configuración
│   ├── tests/                        # Tests
│   ├── Dockerfile                    # Docker image
│   ├── pyproject.toml                # Dependencias Python
│   └── .env                          # Variables de entorno
│
├── 📂 front/                         # Frontend Next.js (Puerto 3000)
│   ├── public/                       # Assets estáticos
│   ├── src/
│   │   ├── app/                      # Next.js App Router
│   │   │   ├── dashboard/            # Dashboard principal
│   │   │   ├── login/                # Login
│   │   │   ├── survey/               # Encuestas públicas
│   │   │   ├── layout.tsx            # Layout raíz
│   │   │   └── page.tsx              # Home
│   │   ├── components/               # Componentes React
│   │   │   ├── features/             # Por funcionalidad
│   │   │   │   ├── diagnostics/      # Diagnósticos
│   │   │   │   ├── survey/           # Encuestas
│   │   │   │   ├── admin/            # Admin panel
│   │   │   │   └── compliance/       # Compliance
│   │   │   ├── layout/               # Header, Sidebar
│   │   │   ├── ui/                   # Componentes base
│   │   │   └── providers/            # Context providers
│   │   ├── styles/                   # CSS
│   │   │   └── globals.css           # Estilos globales
│   │   ├── lib/                      # Librerías
│   │   │   ├── api/                  # Clientes API
│   │   │   │   ├── client.ts         # HTTP client
│   │   │   │   └── auth.ts           # Auth API
│   │   │   ├── types/                # TypeScript types
│   │   │   └── utils/                # Utilidades
│   │   │       ├── helpers.ts        # Helpers generales
│   │   │       ├── validation.ts     # Validaciones
│   │   │       └── geo.ts            # Geo utils
│   │   ├── config/                   # Configuración
│   │   │   └── pipeline-presets.ts   # Presets
│   │   ├── context/                  # React Context
│   │   │   └── AuthContext.tsx       # Auth context
│   │   ├── i18n/                     # i18n config
│   │   └── messages/                 # Traducciones
│   │       ├── es.json               # Español
│   │       └── en.json               # Inglés
│   ├── Dockerfile                    # Docker image
│   ├── package.json                  # Dependencias npm
│   ├── tsconfig.json                 # TypeScript config
│   ├── tailwind.config.ts            # Tailwind config
│   └── README.md                     # Documentación
│
├── 📄 docker-compose.yml             # Orquestación de servicios
├── 📄 .env                           # Variables de entorno
├── 📄 .env.example                   # Ejemplo de .env
├── 📄 .gitignore                     # Git ignore
├── 📄 README.md                      # Documentación principal
├── 📄 start.bat                      # Script de inicio
└── 📄 stop.bat                       # Script de parada
```

## 🎯 Principios de Organización

### 1. **Separación de Concerns**
- **back/**: Gobernanza y políticas (stateless)
- **back-api/**: Orquestación y persistencia (stateful)
- **front/**: Interfaz de usuario

### 2. **Estructura por Funcionalidad**
- Componentes agrupados por feature, no por tipo
- APIs organizadas por dominio
- Tests junto al código que prueban

### 3. **Configuración Centralizada**
- Variables de entorno en `.env`
- Configuración de app en `config/`
- Specs JSON en `specs/`

### 4. **Documentación Cercana al Código**
- README en cada carpeta principal
- Docs técnicos en `docs/`
- Comentarios inline en código complejo

## 🔄 Flujo de Datos

```
Frontend (3000)
    ↓ HTTP
Pipeline API (8000) ←→ Governance (8088)
    ↓                      ↓
Worker                 Evidence Ledger
    ↓
PostgreSQL (5434)
```

## 📦 Dependencias Principales

### Backend (Python)
- FastAPI
- SQLAlchemy
- Alembic
- Google Generative AI
- OPA (Open Policy Agent)

### Frontend (TypeScript)
- Next.js 14
- React 18
- Tailwind CSS
- Radix UI
- React Hook Form
- Recharts

## 🚀 Comandos Rápidos

```bash
# Iniciar todo
docker-compose up -d

# Ver logs
docker-compose logs -f

# Reiniciar API
docker-compose restart api worker

# Detener todo
docker-compose down

# Limpiar y reiniciar
docker-compose down -v && docker-compose up -d
```

## 📊 Métricas del Proyecto

- **Servicios:** 6 (postgres, redis, governance, api, worker, frontend)
- **Agentes IA:** 18
- **Endpoints API:** ~30
- **Componentes React:** ~50
- **Líneas de código:** ~15,000
- **Tests:** ~40

---

**Última actualización:** Abril 2026
