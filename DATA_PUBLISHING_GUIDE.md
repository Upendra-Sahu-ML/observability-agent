# Data Publishing Guide for Observability Agent UI

This guide provides instructions on how to publish test data to NATS for the Observability Agent UI to consume.

## Available Scripts

There are several scripts available for publishing test data to NATS:

### 1. All-in-One Data Generator

The `generate_all_data.js` script generates and publishes sample data for all components to NATS.

```bash
# Port forward to the NATS server
kubectl port-forward -n observability svc/observability-agent-nats 4222:4222

# In another terminal, run the generate_all_data.js script
cd scripts
node generate_all_data.js [options]
```

Options:
- `--nats-url=<url>`: NATS server URL (default: nats://localhost:4222)
- `--duration=<seconds>`: How long to run in seconds (default: 300)
- `--continuous`: Run continuously (default: false)
- `--services=<list>`: Comma-separated list of services (default: payment-service,order-service,inventory-service,api-gateway)
- `--components=<list>`: Comma-separated list of components to generate data for (default: all)
  - Available components: metrics,logs,deployments,agents,traces,rootcauses,notifications,postmortems,runbooks,alerts

Example:
```bash
node generate_all_data.js --nats-url=nats://localhost:4222 --duration=600 --components=metrics,logs,alerts
```

### 2. Domain-Aware Data Publisher

The `publish_with_domain.js` script publishes sample data to NATS with JetStream domain support.

```bash
# Port forward to the NATS server
kubectl port-forward -n observability svc/observability-agent-nats 4222:4222

# In another terminal, run the publish_with_domain.js script
cd scripts
node publish_with_domain.js [options]
```

Options:
- `--nats-url=<url>`: NATS server URL (default: nats://localhost:4222)
- `--domain=<domain>`: JetStream domain (default: observability-agent)
- `--count=<number>`: Number of items to generate (default: 10)
- `--interval=<ms>`: Interval between publications in ms (default: 1000)
- `--continuous`: Run continuously (default: false)
- `--services=<list>`: Comma-separated list of services (default: payment-service,order-service,inventory-service,api-gateway)

Example:
```bash
node publish_with_domain.js --domain=observability-agent --count=20 --continuous
```

### 3. Kubernetes NATS Publisher

The `publish_to_k8s_nats.js` script publishes sample data directly to the NATS server running in Kubernetes. It automatically sets up port forwarding.

```bash
# Run the publish_to_k8s_nats.js script
cd scripts
node publish_to_k8s_nats.js [options]
```

Options:
- `--count=<number>`: Number of items to generate (default: 10)
- `--interval=<ms>`: Interval between publications in ms (default: 1000)
- `--continuous`: Run continuously (default: false)

Example:
```bash
node publish_to_k8s_nats.js --count=20 --continuous
```

### 4. Test Data Publisher

The `publish_test_data.js` script publishes sample data to NATS with JetStream domain support.

```bash
# Port forward to the NATS server
kubectl port-forward -n observability svc/observability-agent-nats 4222:4222

# In another terminal, run the publish_test_data.js script
cd scripts
node publish_test_data.js [options]
```

Options:
- `--nats-url=<url>`: NATS server URL (default: nats://localhost:4222)
- `--domain=<domain>`: JetStream domain (default: observability-agent)
- `--count=<number>`: Number of items to generate (default: 10)
- `--interval=<ms>`: Interval between publications in ms (default: 1000)
- `--continuous`: Run continuously (default: false)

Example:
```bash
node publish_test_data.js --count=20 --domain=observability-agent
```

### 5. Individual Component Publishers

There are also scripts for publishing data for individual components:

- `publish_metrics.js`: Publishes metrics data
- `publish_logs.js`: Publishes logs data
- `publish_alerts.js`: Publishes alerts data
- `publish_agent_status.js`: Publishes agent status data
- `publish_deployments.js`: Publishes deployment data
- `publish_traces.js`: Publishes tracing data
- `publish_rootcauses.js`: Publishes root cause analysis data
- `publish_notifications.js`: Publishes notification data
- `publish_postmortems.js`: Publishes postmortem data
- `publish_runbooks.js`: Publishes runbook data

Each of these scripts accepts similar options:
- `--nats-url=<url>`: NATS server URL (default: nats://localhost:4222)
- `--count=<number>`: Number of items to generate (default: 10)

Example:
```bash
node publish_metrics.js --count=20
node publish_logs.js --count=20
node publish_alerts.js --count=20
```

## Recommended Approach

For testing the UI backend with the NATS domain fix, we recommend using the `publish_with_domain.js` script as it explicitly supports the JetStream domain parameter:

```bash
# Port forward to the NATS server
kubectl port-forward -n observability svc/observability-agent-nats 4222:4222

# In another terminal, run the publish_with_domain.js script
cd scripts
node publish_with_domain.js --domain=observability-agent --count=20 --continuous
```

This will continuously publish metrics, logs, and alerts data to NATS with the correct domain, which should be picked up by the UI backend if the connection is working properly.

## Troubleshooting

If you're still experiencing issues with the UI backend not receiving data from NATS, try the following:

1. **Check NATS Connection**: Make sure the UI backend can connect to NATS by checking the logs.

2. **Verify Streams Exist**: Use the `test_nats_connection.js` script to verify that the required streams exist in NATS.

3. **Check Domain Configuration**: Make sure the NATS server is configured with the correct domain in the `nats.conf` file.

4. **Restart the UI Backend**: Try restarting the UI backend deployment to ensure it picks up the new configuration.

5. **Check for Errors**: Look for any error messages in the UI backend logs that might indicate what's going wrong.
