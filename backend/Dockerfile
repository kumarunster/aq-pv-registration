# Build-Kontext ist das PROJEKTWURZELVERZEICHNIS, nicht backend/.
# Grund: die Datei VERSION liegt im Wurzel und gilt fuer das ganze
# Monorepo. Entsprechend sind alle COPY-Pfade mit backend/ vorangestellt.

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Berlin

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY backend/requirements.txt backend/requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Entwicklungswerkzeuge (Tests) nur im Dev-Build.
ARG INSTALL_DEV=true
RUN if [ "$INSTALL_DEV" = "true" ]; then \
      pip install --no-cache-dir -r requirements-dev.txt ; \
    fi

ENV PYTHONPATH=/app

# Gemeinsame Projektversion. Liegt bewusst ausserhalb von /app: im
# Dev-Betrieb haengt dort ein Bind-Mount des Quellordners, der alles
# darunter verdeckt.
COPY VERSION /opt/app-version

# Application code
COPY backend/ ./

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
