# Observability Agent Test Scripts

This directory contains **Python and bash scripts** for testing the **simplified, consolidated** Observability Agent System. These tools help you test the system with dummy data and validate functionality without requiring external dependencies like Prometheus, Loki, or ArgoCD.

## 🎯 Key Features

- **No External Dependencies**: Works with kubectl fallbacks when external services aren't available
- **Simplified Architecture**: Tests the 4-agent consolidated system (down from 10+ agents)
- **Essential Tools Only**: Uses 15 core tools instead of 50+ complex tools
- **Tiered Testing**: Supports basic, standard, and advanced deployment modes
- **Python-Based**: All scripts are now Python-based for better maintainability

## 🚀 Quick Start

### Prerequisites

```bash
# Install Python dependencies
pip install -r requirements.txt

# Or install manually
pip install nats-py
```

### Run Full Test Suite

```bash
# Run everything in one command
./run_tests.sh full

# Or run individual steps
./run_tests.sh setup      # Setup NATS streams
./run_tests.sh generate   # Generate test data
./run_tests.sh test       # Run system tests
./run_tests.sh health     # Check system health
```

## 📁 Available Scripts

### 🔧 Main Scripts

| Script | Description | Usage |
|--------|-------------|-------|
| `run_tests.sh` | **Main test runner** - orchestrates all testing | `./run_tests.sh [command]` |
| `generate_test_data.py` | **Test data generator** - creates realistic dummy data | `./generate_test_data.py --type=all` |
| `nats_utils.py` | **NATS utilities** - manage streams and messages | `./nats_utils.py setup` |
| `test_system.py` | **System tester** - validates entire system | `./test_system.py --test=all` |

### 🛠️ Infrastructure Scripts

| Script | Description | Usage |
|--------|-------------|-------|
| `deploy-tiered.sh` | **Deployment script** - supports basic/standard/advanced modes | `./deploy-tiered.sh --mode=basic` |
| `manage_nats.sh` | **NATS management** - cleanup and maintenance | `./manage_nats.sh cleanup` |

## 🧪 Testing Scenarios

### Scenario 1: Basic System Test

```bash
# Test with minimal dependencies
./run_tests.sh setup
./run_tests.sh generate --type=alerts --count=5
./run_tests.sh test
```

### Scenario 2: Full System Test

```bash
# Test all components
./run_tests.sh full
```

### Scenario 3: Specific Component Test

```bash
# Test only observability tools
./test_system.py --test=observability

# Test only simplified tools
./test_system.py --test=tools

# Test only agent architecture
./test_system.py --test=agents
```

## 🔍 Test Data Types

The system generates realistic test data for:

- **Alerts**: Simulated incidents and alerts
- **Metrics**: CPU, memory, request rates, error rates
- **Logs**: Application logs with various severity levels
- **Deployments**: Kubernetes deployment status and history
- **Agent Status**: Health and performance of observability agents

### Generate Specific Data Types

```bash
# Generate 10 test alerts
./generate_test_data.py --type=alerts --count=10

# Generate 50 metrics data points
./generate_test_data.py --type=metrics --count=50

# Generate 100 log entries
./generate_test_data.py --type=logs --count=100

# Generate all types
./generate_test_data.py --type=all
```

## 🏗️ System Architecture Testing

### Test the 4-Agent Consolidated Architecture

```bash
# Test that all 4 agents are properly configured
./test_system.py --test=agents

# Expected agents:
# - observability_agent (replaces metric, log, tracing agents)
# - infrastructure_agent (replaces deployment, runbook agents)  
# - communication_agent (replaces notification, postmortem agents)
# - root_cause_agent (enhanced root cause analysis)
```

### Test Simplified Tools (15 instead of 50+)

```bash
# Test essential tools functionality
./test_system.py --test=tools

# Tool categories:
# - 5 Observability tools
# - 5 Kubernetes tools
# - 3 Runbook tools
# - 2 Notification tools
```

## 🔄 Fallback Strategy Testing

The system is designed to work without external dependencies:

```bash
# Test with no Prometheus/Loki/ArgoCD
./test_system.py --test=observability

# System will automatically:
# - Use kubectl fallbacks for metrics
# - Use kubectl fallbacks for logs  
# - Skip tracing if Tempo unavailable
# - Use basic Kubernetes commands
```

## 📊 NATS Stream Management

### Setup and Manage Streams

```bash
# Setup all required streams
./nats_utils.py setup

# List all streams
./nats_utils.py list

# Get stream information
./nats_utils.py info --stream=ALERTS

# Check system health
./nats_utils.py health

# Clean up test data
./nats_utils.py purge --stream=METRICS
```

## 🎛️ Tiered Deployment Testing

### Test Different Deployment Modes

```bash
# Test basic mode (minimal resources)
./deploy-tiered.sh --mode=basic --api-key=your-key --dry-run

# Test standard mode (full observability)
./deploy-tiered.sh --mode=standard --api-key=your-key --dry-run

# Test advanced mode (all features)
./deploy-tiered.sh --mode=advanced --api-key=your-key --dry-run
```

## 🔧 Configuration Options

### Environment Variables

```bash
# NATS server URL
export NATS_URL="nats://localhost:4222"

# OpenAI API key for agents
export OPENAI_API_KEY="your-api-key"

# Deployment mode
export DEPLOYMENT_MODE="basic"  # or "standard" or "advanced"
```

### Command Line Options

```bash
# Specify NATS URL
./run_tests.sh test --nats-url=nats://remote:4222

# Use different Python command
./run_tests.sh setup --python=python3.9

# Generate specific amount of data
./run_tests.sh generate --count=100 --type=metrics
```

## 📋 Expected Test Results

When running the full test suite, you should see:

✅ **NATS Connectivity** - Basic NATS connection works  
✅ **JetStream Functionality** - Stream creation and messaging works  
✅ **Stream Setup** - All 8 required streams are created  
✅ **Alert Processing** - Alerts can be published and processed  
✅ **Simplified Tools** - 15 essential tools are working  
✅ **Observability Manager** - Fallback strategies work  
✅ **Agent Architecture** - 4 consolidated agents are configured  
✅ **Deployment Configurations** - Tiered modes are available  

## 🐛 Troubleshooting

### Common Issues

1. **NATS Connection Failed**
   ```bash
   # Check if NATS is running
   kubectl get pods -n observability
   
   # Or start NATS locally
   docker run -p 4222:4222 nats:latest
   ```

2. **Missing Dependencies**
   ```bash
   # Install Python requirements
   pip install -r requirements.txt
   ```

3. **Agent Tests Fail**
   ```bash
   # Check if agent files exist
   ls -la ../agents/*/agent.py
   ```

4. **Kubectl Fallbacks Not Working**
   ```bash
   # Check kubectl access
   kubectl get pods
   kubectl get deployments
   ```

## 🎉 Success Criteria

Your system is ready when:

- All 8 tests pass in the comprehensive test suite
- NATS streams are created and accessible
- Test data can be generated and published
- Agents can process alerts with fallback strategies
- UI can display the generated test data
- System works without external observability tools

## 📚 Additional Resources

- [CLAUDE.md](../CLAUDE.md) - Development commands and architecture
- [Helm Charts](../helm/observability-agent/) - Deployment configurations
- [Agent Documentation](../agents/) - Individual agent details
- [Common Tools](../common/) - Shared utilities and managers

This testing approach ensures the simplified observability system works reliably across different environments and deployment modes.