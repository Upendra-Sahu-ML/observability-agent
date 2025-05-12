# Root Cause Agent

The Root Cause Agent is a critical component of the Observability Agent system responsible for synthesizing analyses from all specialized agents to determine the most likely root cause of system incidents.

## Overview

The Root Cause Agent uses AI-powered analysis to combine insights from the Metric, Log, Deployment, and Tracing agents. It analyzes the correlations between different data sources to identify the underlying cause of system incidents and suggest remediation steps.

## Functionality

- **Multi-Agent Synthesis**: Combines analyses from specialized agents
- **Evidence Correlation**: Correlates evidence across different observability domains
- **Root Cause Determination**: Identifies the most likely underlying cause of incidents
- **Remediation Suggestions**: Proposes steps to address the identified root cause
- **Confidence Assessment**: Provides confidence level in its determinations

## Key Components

Unlike other agents, the Root Cause Agent doesn't directly interact with external systems. Instead, it focuses on synthesizing and analyzing the insights provided by the specialized agents.

## How It Works

1. The agent listens on the "root_cause_analysis" Redis channel for comprehensive data from the Orchestrator
2. When comprehensive data is received, the agent:
   - Extracts analyses from all specialized agents (metric, log, deployment, tracing)
   - Uses CrewAI with GPT-4 to synthesize the analyses
   - Determines the most likely root cause based on evidence from all domains
   - Identifies supporting evidence for its determination
   - Suggests remediation steps to address the root cause
   - Sends the root cause analysis back to the Orchestrator via the "root_cause_result" channel

## Configuration

The Root Cause Agent can be configured with the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_HOST` | Redis host for message communication | `redis` |
| `REDIS_PORT` | Redis port for message communication | `6379` |
| `OPENAI_API_KEY` | OpenAI API key for root cause analysis | None (required) |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4` |
| `RESPONSE_TIMEOUT_SECONDS` | Timeout for waiting on agent responses | `300` |

## Customization

To modify the root cause analysis behavior:

1. Update the `analyze_root_cause()` method to adjust how analyses are synthesized
2. Modify the prompt template to focus on specific types of patterns or issues
3. Add additional synthesis logic to better correlate evidence across domains

## Local Development

```bash
# Run the Root Cause Agent standalone
cd agents/root_cause_agent
python main.py
```

## Docker

Build and run the Root Cause Agent as a Docker container:

```bash
docker build -t root-cause-agent -f agents/root_cause_agent/Dockerfile .
docker run -e OPENAI_API_KEY=your_key root-cause-agent
```

## Integration

The Root Cause Agent is designed to work as the culmination of the Observability Agent system. It:
- Receives comprehensive data from the Orchestrator
- Synthesizes analyses from all specialized agents
- Determines the most likely root cause of incidents
- Suggests remediation steps
- Provides the final output of the entire observability system