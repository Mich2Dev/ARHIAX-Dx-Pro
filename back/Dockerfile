FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ARHIAX_DX_ENV=production

COPY pyproject.toml ./
COPY src ./src
COPY docs ./docs
COPY specs ./specs
COPY policies ./policies

RUN pip install --no-cache-dir .

RUN addgroup --system arhiax && adduser --system --ingroup arhiax arhiax
RUN mkdir -p /app/var && chown -R arhiax:arhiax /app

USER arhiax

EXPOSE 8088

CMD ["uvicorn", "arhiax_dx.main:app", "--host", "0.0.0.0", "--port", "8088", "--app-dir", "src"]
