# Build stage
FROM node:18-alpine AS build
WORKDIR /app

# Copy package.json and install dependencies
COPY package.json ./
RUN npm install

# Copy all source files
COPY . .

# Build the app with increased memory allocation
ENV NODE_OPTIONS="--max-old-space-size=4096"
RUN npm run build

# Production stage
FROM nginx:stable-alpine
WORKDIR /usr/share/nginx/html

# Install envsubst for environment variable substitution
RUN apk add --no-cache bash gettext

# Remove default nginx static assets
RUN rm -rf ./*

# Copy static assets from builder stage
COPY --from=build /app/build .

# Copy nginx configuration template
COPY nginx.conf /etc/nginx/nginx.conf.template

# Configure nginx for logging to stdout/stderr
RUN ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log

# Expose port 80
EXPOSE 80

# Create a separate entrypoint script file
RUN echo '#!/bin/sh' > /docker-entrypoint.sh && \
    echo 'set -e' >> /docker-entrypoint.sh && \
    echo '' >> /docker-entrypoint.sh && \
    echo '# Set default value for BACKEND_SERVICE_URL if not provided' >> /docker-entrypoint.sh && \
    echo 'export BACKEND_SERVICE_URL=${BACKEND_SERVICE_URL:-http://localhost:5000}' >> /docker-entrypoint.sh && \
    echo '# Set default value for K8S_COMMAND_SERVICE_URL if not provided' >> /docker-entrypoint.sh && \
    echo 'export K8S_COMMAND_SERVICE_URL=${K8S_COMMAND_SERVICE_URL:-http://localhost:5002}' >> /docker-entrypoint.sh && \
    echo '' >> /docker-entrypoint.sh && \
    echo '# Process the nginx config template' >> /docker-entrypoint.sh && \
    echo 'envsubst "\${BACKEND_SERVICE_URL} \${K8S_COMMAND_SERVICE_URL}" < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf' >> /docker-entrypoint.sh && \
    echo '' >> /docker-entrypoint.sh && \
    echo '# Start nginx' >> /docker-entrypoint.sh && \
    echo 'exec nginx -g "daemon off;"' >> /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

# Start nginx with environment variable substitution
ENTRYPOINT ["/docker-entrypoint.sh"]
