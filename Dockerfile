FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV ARHIAX_DX_SPECS_PATH=/app/back/specs
ENV ARHIAX_DX_LEDGER_PATH=/app/back/var/evidence-ledger.jsonl

# Instalar dependencias del sistema (Node.js 20, Postgres 15, Redis, Supervisor, Build tools)
RUN apt-get update && apt-get install -y curl gnupg2 sudo supervisor redis-server wget git build-essential \
    && apt-get install -y postgresql fonts-dejavu-core \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar todo el código fuente
COPY . .

# Instalar dependencias de Python para todos los servicios
# Utilizamos el flag --no-deps o instalamos normal, el flag -e puede no ser lo mejor en prod pero servirá para el monolith
RUN pip install --no-cache-dir ./back
RUN pip install --no-cache-dir ./back-api
RUN pip install --no-cache-dir ./ARHIAX-Dx-Pro

# Construir el Frontend (Next.js)
WORKDIR /app/front
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_API_URL=/api/backend
ENV INTERNAL_API_URL=http://localhost:8000
RUN npm install
RUN npm run build
RUN cp -r .next/static .next/standalone/.next/static
RUN cp -r public .next/standalone/public
WORKDIR /app

# Configurar Postgres y Supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY start-cloudrun.sh /start-cloudrun.sh
RUN chmod +x /start-cloudrun.sh
RUN chmod +x /app/start-pg.sh

# Crear carpetas de datos necesarias
RUN mkdir -p /app/ARHIAX-Dx-Pro/data/cases /app/ARHIAX-Dx-Pro/data/exports /app/back/var
RUN touch /app/back/var/evidence-ledger.jsonl /app/ARHIAX-Dx-Pro/data/evidence.jsonl

# Exponer el puerto de Next.js
EXPOSE 3000

CMD ["/start-cloudrun.sh"]
