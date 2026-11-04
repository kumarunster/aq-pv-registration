FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    KATASTER_CURL=/usr/bin/curl

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 kataster \
    && useradd --uid 10001 --gid kataster --no-create-home kataster \
    && mkdir -p /app /data \
    && chown kataster:kataster /data

WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --only-binary=:all: -r requirements.txt

COPY kataster/ ./kataster/

USER 10001:10001
EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=3).close()"]

ENTRYPOINT ["python", "-m", "kataster"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8765", "--output", "/data"]
