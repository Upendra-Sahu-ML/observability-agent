# Root Cause Agent

The Root Cause Agent is a critical component of the Observability Agent system responsible for synthesizing analyses from all specialized agents to determine the most likely root cause of system incidents.

## Overview

The Root Cause Agent uses AI-powered analysis to combine insights from the **consolidated agents** (Observability, Infrastructure, and Communication agents). It analyzes the correlations between different data sources to identify the underlying cause of system incidents and suggest remediation steps.

## Functionality

- **Multi-Agent Synthesis**: Combines analyses from consolidated agents (Observability, Infrastructure, Communication)
- **Evidence Correlation**: Correlates evidence across different observability domains
- **Root Cause Determination**: Identifies the most likely underlying cause of incidents
- **Remediation Suggestions**: Proposes steps to address the identified root cause
- **Confidence Assessment**: Provides confidence level in its determinations

## Key Components

Unlike other agents, the Root Cause Agent doesn't directly interact with external systems. Instead, it focuses on synthesizing and analyzing the insights provided by the specialized agents.

## NATS Integration

The agent integrates with NATS JetStream for messaging and data storage:

### Subscriptions:
- `root_cause_agent`: Receives individual alerts from the orchestrator
- `root_cause_analysis`: Receives comprehensive data from the orchestrator after all agents respond

### Publications:
- `root_cause_result`: Sends analysis results to the orchestrator for runbook and postmortem agents
- `rootcause.{service}`: Stores root cause data for UI consumption in ROOT_CAUSE stream

## How It Works

1. **Individual Alert Processing**: The agent receives individual alerts from the orchestrator on `root_cause_agent` subject
2. **Comprehensive Analysis**: When all agents have responded, the orchestrator sends comprehensive data on `root_cause_analysis` subject
3. **Multi-Agent Analysis**: The agent uses specialized CrewAI agents for different analysis domains:
   - Infrastructure Analyst: Hardware, system-level, and cloud infrastructure issues
   - Application Analyst: Code-level, memory, and runtime issues
   - Database Analyst: Database performance and query issues
   - Network Analyst: Connectivity, latency, and routing problems
   - Root Cause Manager: Synthesizes findings from all specialists
4. **Data Storage**: Results are stored in ROOT_CAUSE stream for UI consumption with structured format
5. **Orchestrator Integration**: Analysis results are sent to orchestrator for downstream processing

## Configuration

The Root Cause Agent can be configured with the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `NATS_URL` | NATS server URL for message communication | `nats://nats:4222` |
| `OPENAI_API_KEY` | OpenAI API key for root cause analysis | None (required) |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4` |

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

The Root Cause Agent is fully integrated with the orchestrator and UI:

**Orchestrator Workflow:**
1. Orchestrator receives alerts and distributes to all consolidated agents including root cause agent
2. Root cause agent receives individual alerts for early processing
3. After all consolidated agents respond, orchestrator sends comprehensive data to root cause agent
4. Root cause agent performs multi-agent analysis using CrewAI
5. Results are sent to orchestrator and stored for UI consumption

**UI Integration:**
- UI backend retrieves root cause data from ROOT_CAUSE stream
- Real-time root cause analysis visualization with confidence levels
- Alert correlation for incident investigation
- Structured analysis with evidence and recommendations

**Data Flow:**
- Individual alerts: `orchestrator` → `root_cause_agent` → `root cause agent`
- Comprehensive data: `orchestrator` → `root_cause_analysis` → `root cause agent`
- Results: `root cause agent` → `root_cause_result` → `orchestrator`
- UI data: `root cause agent` → `rootcause.{service}` → `UI backend`