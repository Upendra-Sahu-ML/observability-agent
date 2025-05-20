# Observability Agent UI Backend

This is the backend service for the Observability Agent UI. It provides API endpoints for the UI to fetch data from the various agents in the system.

## Features

- RESTful API endpoints for all agent data
- NATS integration for real-time data
- Fallback to mock data when NATS is unavailable
- In-memory caching for improved performance
- Health check endpoint

## API Endpoints

The following API endpoints are available:

- `/api/agents` - Get information about all agents
- `/api/metrics` - Get metric data
- `/api/logs` - Get log data
- `/api/deployment` - Get deployment information
- `/api/rootcause` - Get root cause analysis results
- `/api/tracing` - Get tracing data
- `/api/notification` - Get notification data
- `/api/postmortem` - Get postmortem reports
- `/api/runbook` - Get runbook information
- `/health` - Get health status of the backend service

## Query Parameters

Some endpoints support query parameters for filtering:

- `/api/metrics?service=<service-name>` - Filter metrics by service
- `/api/logs?service=<service-name>&startTime=<iso-date>&endTime=<iso-date>` - Filter logs by service and time range
- `/api/rootcause?alertId=<alert-id>` - Filter root cause analysis by alert ID
- `/api/tracing?traceId=<trace-id>&service=<service-name>` - Filter traces by trace ID and service
- `/api/runbook?id=<runbook-id>` - Get a specific runbook by ID

## Installation

```bash
# Install dependencies
npm install

# Start the server
npm start
```

## Environment Variables

- `PORT` - Port to listen on (default: 5001)
- `NATS_URL` - URL of the NATS server (default: nats://nats:4222)

## Docker

```bash
# Build the Docker image
docker build -t observability-agent-backend .

# Run the container
docker run -p 5000:5000 -e NATS_URL=nats://nats:4222 observability-agent-backend
```

## Development

For local development, you can run the server without a NATS connection. It will use mock data instead.

```bash
# Start the server in development mode
npm start
```

## Integration with UI

The UI should be configured to connect to this backend service. Update the `REACT_APP_API_URL` environment variable in the UI's `.env` file to point to this service.

Example:
```
REACT_APP_API_URL=http://localhost:5001/api
```
