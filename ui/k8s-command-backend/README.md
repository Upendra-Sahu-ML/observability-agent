# Kubernetes Command Backend

This is a backend service for the Kubernetes Command Interface, which allows users to run Kubernetes commands using natural language.

## Features

- Convert natural language to Kubernetes commands using OpenAI
- Execute Kubernetes commands and return results
- Save and manage command notebooks
- Export notebooks as runbooks

## API Endpoints

- `GET /health` - Health check endpoint
- `POST /api/convert` - Convert natural language to Kubernetes command
- `POST /api/execute` - Execute Kubernetes command
- `GET /api/notebooks` - Get all notebooks
- `GET /api/notebooks/:id` - Get notebook by ID
- `POST /api/notebooks` - Create a new notebook
- `PUT /api/notebooks/:id` - Update a notebook
- `DELETE /api/notebooks/:id` - Delete a notebook
- `POST /api/notebooks/:id/export` - Export notebook as runbook

## Installation

```bash
# Install dependencies
npm install

# Create .env file
cp .env.example .env
# Edit .env file with your configuration

# Start the server
npm start
```

## Environment Variables

- `PORT` - Port to listen on (default: 5002)
- `MONGODB_URI` - MongoDB connection URI (default: mongodb://localhost:27017/k8s-command)
- `NATS_URL` - NATS server URL (default: nats://localhost:4222)
- `OPENAI_API_KEY` - OpenAI API key

## Docker

```bash
# Build the Docker image
docker build -t k8s-command-backend .

# Run the Docker container
docker run -p 5002:5002 --env-file .env k8s-command-backend
```
