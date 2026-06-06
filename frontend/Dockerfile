# ---- Stage 1: Build der Angular-SPA ----
FROM node:24-alpine AS build
WORKDIR /app

# Abhaengigkeiten zuerst (besseres Layer-Caching)
COPY package.json package-lock.json ./
RUN npm ci

# Quellcode + Produktions-Build
COPY . .
RUN npm run build

# ---- Stage 2: Auslieferung via nginx ----
FROM nginx:1.27-alpine AS serve

# Eigene nginx-Conf (SPA + /api + /ws Proxy zu game-server:8000)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Gebautes Bundle in den Webroot
COPY --from=build /app/dist/universe/browser /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
