# ARHIAX Dx Platform

Plataforma de diagnósticos organizacionales gobernados — Sinergia Consulting Group.

## Inicio rápido

**Requisitos:** Docker Desktop + Node.js 18+

```
Doble clic en start.bat
```

El script instala dependencias, construye las imágenes y levanta todo automáticamente.

## Acceso

| URL | Descripción |
|-----|-------------|
| http://localhost:3000 | Frontend (portal principal) |
| http://localhost:8000 | API Dx Standard |
| http://localhost:8088 | Governance |
| http://localhost:8310 | Dx Pro runtime |

**Credenciales:** `admin@sinergia.co` / `test1234`

## Estructura

```
/
├── front/             # Frontend Next.js
├── back-api/          # API Dx Standard (FastAPI + PostgreSQL)
├── back/              # Servicio de gobernanza
├── ARHIAX-Dx-Pro/     # Runtime Dx Pro standalone
├── docs/              # Documentación del proyecto
├── docker-compose.yml
├── start.bat          # Arranque completo (instala + levanta)
└── .env
```

## Comandos útiles

```bash
# Ver logs
docker compose logs -f

# Reiniciar un servicio
docker compose restart api

# Detener todo
docker compose down
```

## Documentación

- [Estructura del proyecto](docs/ESTRUCTURA.md)
- [Checklist de producción](docs/PRODUCCION_CHECKLIST.md)
- [Arquitectura Dx Pro](ARHIAX-Dx-Pro/docs/ARCHITECTURE.md)
