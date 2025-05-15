# Observability Agent

A distributed observability system that uses AI agents to analyze and respond to system events.

## Architecture

The system consists of several specialized agents:

- **Log Agent**: Analyzes log data to identify patterns and anomalies
- **Metric Agent**: Processes metrics to detect performance issues
- **Tracing Agent**: Analyzes distributed traces to identify bottlenecks
- **Root Cause Agent**: Determines the root cause of issues
- **Postmortem Agent**: Generates postmortem reports
- **Notification Agent**: Handles alerting and notifications
- **Deployment Agent**: Manages deployments and rollbacks

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

3. Run the agents:
```bash
python main.py
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

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT
