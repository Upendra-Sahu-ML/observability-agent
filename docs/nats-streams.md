# NATS Streams Documentation

This document describes the NATS streams used by the observability agent and their purposes.

## Overview

The observability agent uses NATS JetStream for messaging between components. JetStream provides persistent storage for messages, allowing for reliable message delivery and replay.

## Stream Initialization

Streams are initialized in one of the following ways:

1. **NATS Initialization Job**: A Kubernetes job that runs after NATS is deployed to create all required streams.
2. **Agent Initialization**: Each agent checks for required streams during startup and creates them if they don't exist.
3. **Manual Initialization**: The `scripts/init_nats_streams.py` script can be run manually to create all required streams.

## Stream Definitions

The following streams are used by the observability agent:

| Stream Name | Subjects | Purpose | Used By |
|-------------|----------|---------|---------|
| `ALERTS` | `alerts`, `alerts.*` | Stores alert messages from monitoring systems | Orchestrator |
| `AGENT_TASKS` | `metric_agent`, `log_agent`, `deployment_agent`, `tracing_agent`, `root_cause_agent`, `notification_agent`, `postmortem_agent`, `runbook_agent` | Stores tasks for agents | All agents |
| `RESPONSES` | `orchestrator_response`, `root_cause_result` | Stores agent responses to the orchestrator | Orchestrator, All agents |
| `ALERT_DATA` | `alert_data_request`, `alert_data_response.*` | Stores alert data requests and responses | Orchestrator |
| `ROOT_CAUSE` | `root_cause_analysis`, `root_cause_result`, `rootcause`, `rootcause.*` | Stores root cause analysis data | Root Cause Agent |
| `METRICS` | `metrics`, `metrics.*` | Stores metric data | Metric Agent |
| `LOGS` | `logs`, `logs.*` | Stores log data | Log Agent |
| `DEPLOYMENTS` | `deployments`, `deployments.*` | Stores deployment data | Deployment Agent |
| `TRACES` | `traces`, `traces.*` | Stores trace data | Tracing Agent |
| `POSTMORTEMS` | `postmortems`, `postmortems.*` | Stores postmortem data | Postmortem Agent |
| `RUNBOOKS` | `runbooks`, `runbooks.*`, `runbook`, `runbook.*` | Stores runbook data | Runbook Agent |
| `RUNBOOK_EXECUTIONS` | `runbook.execute`, `runbook.status.*` | Stores runbook execution data | Runbook Agent |
| `NOTEBOOKS` | `notebooks`, `notebooks.*` | Stores notebook data | Notebook Agent |
| `NOTIFICATIONS` | `notification_requests`, `notifications`, `notifications.*` | Stores notification data | Notification Agent |

## Stream Configuration

All streams are configured with the following settings:

- **Retention**: `limits` - Messages are retained until limits are reached
- **Max Messages**: 10,000 - Maximum number of messages per stream
- **Max Bytes**: 100MB - Maximum size of the stream
- **Max Age**: 7 days - Maximum age of messages
- **Storage**: `memory` - Messages are stored in memory
- **Discard**: `old` - Oldest messages are discarded when limits are reached

## Troubleshooting

If agents are failing with "stream not found" errors, you can run the initialization script to create the missing streams:

```bash
# Run the initialization script
./scripts/run_nats_init.sh
```

You can also check the existing streams using the NATS CLI:

```bash
# Port-forward to the NATS server
kubectl port-forward -n observability svc/observability-agent-nats 8222:8222

# Check the streams
curl -s http://localhost:8222/jsz
```

## Adding New Streams

To add a new stream:

1. Add the stream definition to the `js-streams.json` file in the NATS ConfigMap
2. Update the `init_nats_streams.py` script to include the new stream
3. Run the initialization script to create the new stream

## Best Practices

1. **Centralized Stream Creation**: Use the initialization job to create all streams instead of having each agent create its own streams.
2. **Stream Naming**: Use uppercase names for streams and lowercase for subjects.
3. **Subject Naming**: Use descriptive names for subjects and include wildcards where appropriate.
4. **Stream Monitoring**: Monitor stream usage to ensure limits are not exceeded.
