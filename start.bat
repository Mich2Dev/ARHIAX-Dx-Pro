@echo off
title ARHIAX Dx — Setup y arranque
chcp 65001 >nul 2>&1

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║         ARHIAX Dx Platform               ║
echo  ║         Setup + Arranque completo        ║
echo  ╚══════════════════════════════════════════╝
echo.

:: ── Verificar Docker ─────────────────────────────────────────────────────────
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker Desktop no esta corriendo.
    echo         Abrelo y vuelve a ejecutar este script.
    pause
    exit /b 1
)

:: ── Verificar .env ───────────────────────────────────────────────────────────
if not exist .env (
    echo [AVISO] No se encontro .env — copiando desde .env.example...
    copy .env.example .env >nul
    echo         Edita .env y agrega GEMINI_API_KEY si tienes una.
    echo.
)

:: ── Levantar servicios con Docker ──────────────────────────────────────────
echo [1/1] Levantando todos los servicios (Backend, Frontend, DBs)...
docker-compose up -d --build
if %errorlevel% neq 0 (
    echo [ERROR] docker-compose fallo.
    echo         Revisa los logs con: docker-compose logs
    pause
    exit /b 1
)

:: ── Resumen ───────────────────────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║  Listo. Abre el navegador en:            ║
echo  ║                                          ║
echo  ║    http://localhost:3000                 ║
echo  ║                                          ║
echo  ║  Login:  admin@sinergia.co               ║
echo  ║  Pass:   test1234                        ║
echo  ╚══════════════════════════════════════════╝
echo.
echo  Comandos utiles:
echo    Ver logs:    docker-compose logs -f
echo    Detener:     docker-compose down
echo.
pause
