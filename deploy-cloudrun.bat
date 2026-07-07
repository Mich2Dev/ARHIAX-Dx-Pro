@echo off
title Deploy ARIHAX-Dx-Pro to Google Cloud Run
chcp 65001 >nul 2>&1

echo ========================================================
echo   Desplegando ARIHAX-Dx-Pro a Google Cloud Run
echo ========================================================
echo.
echo Esto empaquetara TODOS los servicios en un solo contenedor
echo monolítico. Asegurate de tener gcloud instalado.
echo.

set PROJECT_ID=arhiax-project
set REGION=southamerica-east1
set SERVICE_NAME=arhiax-dx-pro
set CLOUDSQL=arhiax-project:southamerica-east1:arhiax-db
set APP_URL=https://arhiax-dx-pro-187668243215.southamerica-east1.run.app

echo [1/1] Build + deploy en Cloud Run (Cloud Build desde fuente)...
call gcloud run deploy %SERVICE_NAME% ^
    --source . ^
    --project %PROJECT_ID% ^
    --region %REGION% ^
    --memory 4Gi ^
    --cpu 2 ^
    --port 3000 ^
    --allow-unauthenticated ^
    --timeout=3600 ^
    --add-cloudsql-instances %CLOUDSQL% ^
    --update-env-vars APP_URL=%APP_URL%

if %errorlevel% neq 0 (
    echo [ERROR] Fallo el deploy en Cloud Run.
    pause
    exit /b %errorlevel%
)

echo ========================================================
echo ¡Despliegue completado con exito!
echo ========================================================
pause
