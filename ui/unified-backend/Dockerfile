FROM node:18-alpine

WORKDIR /app

# Install system dependencies for Azure CLI, kubectl, and API tools
RUN apk add --no-cache \
    curl \
    wget \
    bash \
    python3 \
    py3-pip \
    ca-certificates \
    gnupg

# Install Azure CLI (Alpine version)
RUN apk add --no-cache --virtual .build-deps gcc musl-dev libffi-dev openssl-dev python3-dev \
    && pip3 install azure-cli \
    && apk del .build-deps

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY . .

# Copy shared utilities from original backends
COPY ../backend/alerts.js ./
COPY ../backend/knowledge.js ./
COPY ../backend/constants.js ./

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001

# Change ownership
RUN chown -R nodejs:nodejs /app

USER nodejs

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/api/agents || exit 1

CMD ["npm", "start"]