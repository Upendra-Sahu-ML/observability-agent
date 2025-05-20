# Dockerfile for UI backend service
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install --production

# Copy application code
COPY server.js ./
COPY alerts.js ./
COPY knowledge.js ./

# Set environment variables
ENV NODE_ENV=production
ENV PORT=5000
ENV NATS_URL=nats://nats:4222

# Expose the port
EXPOSE 5000

# Start the application
CMD ["node", "server.js"]
