FROM node:18-alpine

WORKDIR /app

# Install kubectl and dependencies
RUN apk add --no-cache curl bash ca-certificates && \
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 5002

CMD ["node", "server.js"]
