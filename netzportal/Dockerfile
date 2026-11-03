# syntax=docker/dockerfile:1
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    NRM_HOST=0.0.0.0 \
    NRM_PORT=8080 \
    PV_DATA_DIR=/data

WORKDIR /app

# Copy only runtime inputs. Credentials and local artifacts never enter the image.
COPY pyproject.toml ./
COPY nrm_api/ ./nrm_api/
RUN python -m pip install . \
    && groupadd --gid 10001 nrm \
    && useradd --uid 10001 --gid nrm --no-create-home --shell /usr/sbin/nologin nrm \
    && mkdir -p /data && chown 10001:10001 /data && chmod 700 /data

USER 10001:10001
EXPOSE 8080

# Process liveness only: this never signs in to NRM or reads customer records.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3).close()"]

CMD ["python", "-m", "nrm_api"]
