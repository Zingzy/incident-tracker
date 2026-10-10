FROM node:22-alpine AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY index.html vite.config.js ./
COPY src ./src
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.30-alpine
# The base image lags Alpine security fixes, which Trivy flags.
USER root
RUN apk upgrade --no-cache
USER 101
ENV BACKEND_HOST=backend
COPY --from=build /src/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
EXPOSE 8080
