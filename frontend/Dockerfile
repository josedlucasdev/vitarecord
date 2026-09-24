# ==========================================
# Stage 1: Build Quasar SPA
# ==========================================
FROM node:20-slim AS builder

WORKDIR /app

# Copy dependency manifests
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application source code
COPY . .

# Environment variables for production build
ARG API_URL=https://api.vitarecord.com
ENV API_URL=$API_URL
ENV CLIENT_API_URL=$API_URL
ENV VITE_API_URL=$API_URL

# Build Quasar SPA output into dist/spa
RUN npm run build

# ==========================================
# Stage 2: Serve SPA with Nginx
# ==========================================
FROM nginx:alpine

# Copy custom Nginx configuration for Quasar SPA
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled SPA static files from builder
COPY --from=builder /app/dist/spa /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
