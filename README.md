# Observability Agent

A distributed observability system that uses AI agents to analyze and respond to system events.

## Architecture

The system consists of several specialized agents and components:

- **Log Agent**: Analyzes log data to identify patterns and anomalies
- **Metric Agent**: Processes metrics to detect performance issues
- **Tracing Agent**: Analyzes distributed traces to identify bottlenecks
- **Root Cause Agent**: Determines the root cause of issues
- **Postmortem Agent**: Generates postmortem reports
- **Notification Agent**: Handles alerting and notifications
- **Deployment Agent**: Manages deployments and rollbacks
- **UI Backend**: Provides API endpoints for the UI
- **UI**: Web interface for interacting with the system
- **K8s Command Backend**: Converts natural language to Kubernetes commands and executes them

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run the system using Docker Compose:
```bash
docker-compose up -d
```

4. Access the UI:
```bash
# UI is available at http://localhost:8080
# UI Backend API is available at http://localhost:5000/api
# K8s Command Backend API is available at http://localhost:5002/api
```

## Development

### Testing
```bash
pytest tests/
```

### Adding New Tools

1. Create a new tool class in `common/tools/`
2. Implement the tool using crewai's BaseTool
3. Add the tool to the appropriate agent
4. Update tests

### Adding New Agents

1. Create a new agent class in `agents/`
2. Implement the agent using crewai's Agent
3. Add the agent to main.py
4. Create tests

## Documentation

- [Kubernetes Command Interface](docs/K8S_COMMAND_INTERFACE.md) - Overview of the Kubernetes Command Interface
- [Kubernetes Command Examples](docs/K8S_COMMAND_EXAMPLES.md) - Examples of natural language queries for Kubernetes

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT
