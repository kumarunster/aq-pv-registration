FROM python:3.12-slim

# WeasyPrint-System-Abhaengigkeiten (Pango, Cairo, Fontconfig) + Schriften
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfontconfig1 \
    fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN pip install --no-cache-dir weasyprint

COPY server.py .
EXPOSE 8012
CMD ["python", "server.py"]
