# Build-Kontext ist das PROJEKTWURZELVERZEICHNIS, nicht frontend/.
# Grund: die Datei VERSION im Wurzel gilt fuer das ganze Monorepo.

# --- Build ---
FROM node:22-alpine AS build

WORKDIR /app

COPY frontend/package*.json ./
RUN npm install

# Vor dem Quelltext kopieren: vite.config.js liest die Datei beim Build.
COPY VERSION /VERSION

COPY frontend/ ./
RUN npm run build

# --- Serve ---
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx-spa.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
