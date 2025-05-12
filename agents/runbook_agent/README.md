# Runbook Agent

The Runbook Agent is a specialized component of the Observability Agent system dedicated to validating, enhancing, and adapting existing runbooks based on root cause analysis to provide accurate remediation steps for incidents.

## Overview

The Runbook Agent uses AI-powered analysis to evaluate existing runbooks against the determined root cause of an incident. It identifies gaps or inaccuracies in predefined runbooks and enhances them with more appropriate remediation steps specific to the actual cause of the incident.

## Functionality

- **Runbook Retrieval**: Fetches existing runbooks from multiple sources (GitHub, HTML pages, local files)
- **Root Cause Integration**: Analyzes root cause findings to validate or challenge existing runbook steps
- **Runbook Enhancement**: Uses AI to improve, correct, or create new runbook steps as needed
- **Step Verification**: Adds verification steps to confirm the remediation is effective
- **Response Publishing**: Provides enhanced runbooks with practical, actionable remediation steps

## Key Components

- **RunbookAgent**: Coordinates the runbook enhancement process and integrates with the observability system
- **Runbook Enhancer**: A specialized CrewAI agent that evaluates and enhances runbooks based on root cause analysis
- **RunbookFetchTool**: Fetches runbooks from multiple sources in order of priority

## Runbook Sources

The agent can fetch runbooks from multiple sources:

1. **Local Files**: Markdown runbooks stored in the local filesystem
2. **GitHub Repositories**: Markdown runbooks stored in GitHub repositories
3. **HTML Pages**: Runbooks published on GitHub Pages or other HTML websites

## How It Works

1. The agent listens on the "root_cause_result" Redis channel for root cause analysis results
2. When root cause analysis is received, the agent:
   - Retrieves the original alert data (either from Redis cache or by requesting it from the orchestrator)
   - Fetches any existing runbook for the alert from configured sources
   - Uses CrewAI with GPT-4 to analyze the root cause findings and existing runbook
   - Validates the existing runbook steps against the root cause
   - Enhances or corrects the runbook as needed
   - Sends the enhanced runbook to the "enhanced_runbook" channel

## Configuration

The Runbook Agent can be configured with the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_HOST` | Redis host for message communication | `redis` |
| `REDIS_PORT` | Redis port for message communication | `6379` |
| `OPENAI_API_KEY` | OpenAI API key for runbook enhancement | None (required) |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4` |
| `RUNBOOK_LOCAL_PATH` | Path to local runbook files | `/runbooks` |
| `RUNBOOK_GITHUB_REPO` | GitHub repository with runbooks in format "owner/repo" | None |
| `RUNBOOK_GITHUB_BRANCH` | Branch name for GitHub runbooks | `main` |
| `RUNBOOK_GITHUB_PATH` | Path to runbooks directory in GitHub repo | `runbooks` |
| `GITHUB_TOKEN` | GitHub personal access token for private repositories | None |
| `RUNBOOK_HTML_BASE_URL` | Base URL for HTML runbooks | None |

## Customization

To modify the runbook enhancement behavior:

1. Update the `enhance_runbook()` method to adjust the enhancement prompt
2. Modify the runbook tools to support additional sources or parsing strategies
3. Add new validation or scoring mechanisms to better evaluate runbooks

## Local Development

```bash
# Run the Runbook Agent standalone
cd agents/runbook_agent
python main.py
```

## Docker

Build and run the Runbook Agent as a Docker container:

```bash
docker build -t runbook-agent -f agents/runbook_agent/Dockerfile .
docker run -e OPENAI_API_KEY=your_key -e RUNBOOK_GITHUB_REPO=your-org/runbooks runbook-agent
```

## Integration

The Runbook Agent is designed to work as part of the Observability Agent system. It:
- Receives root cause analysis from the Root Cause Agent
- Enhances existing runbooks with practical remediation steps
- Publishes enhanced runbooks that can be used to resolve incidents
- Acts as the final step in the incident analysis and remediation pipeline