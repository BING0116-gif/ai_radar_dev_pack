# syntax=docker/dockerfile:1
# --- build stage: compile the Vue app ---------------------------------------
FROM node:22-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.js ./
COPY src ./src
RUN npm run build

# --- runtime stage: nginx serves the static build + proxies /api -------------
FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80