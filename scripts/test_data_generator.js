#!/usr/bin/env node
/**
 * Test Data Generator for Observability Agent UI
 * 
 * This script tests the data generation functions without requiring a NATS server.
 * It generates sample data for all components and outputs it to the console.
 * 
 * Usage:
 *   node test_data_generator.js [options]
 * 
 * Options:
 *   --component=<name>     Component to test (default: all)
 *   --count=<number>       Number of items to generate (default: 3)
 *   --services=<list>      Comma-separated list of services (default: payment-service,order-service,inventory-service,api-gateway)
 * 
 * Example:
 *   node test_data_generator.js --component=metrics --count=5
 */

const utils = require('./nats_utils');

// Parse command line arguments
const args = process.argv.slice(2).reduce((acc, arg) => {
  if (arg.startsWith('--')) {
    const [key, value] = arg.substring(2).split('=');
    acc[key] = value !== undefined ? value : true;
  }
  return acc;
}, {});

// Configuration with defaults
const config = {
  component: args['component'] || 'all',
  count: parseInt(args['count'] || '3'),
  services: (args['services'] || 'payment-service,order-service,inventory-service,api-gateway').split(',')
};

// Import generator functions from each script
const generateMetric = () => {
  const service = utils.randomItem(config.services);
  const metricTypes = [
    { name: 'CPU Usage', unit: '%', min: 0, max: 100, format: (val) => `${val}%` },
    { name: 'Memory Usage', unit: 'MB', min: 100, max: 8192, format: (val) => `${val}MB` },
    { name: 'Request Rate', unit: 'req/s', min: 10, max: 500, format: (val) => `${val} req/s` },
    { name: 'Error Rate', unit: '%', min: 0, max: 10, format: (val) => `${val}%` }
  ];
  const metricType = utils.randomItem(metricTypes);
  const rawValue = utils.randomNumber(metricType.min, metricType.max);
  
  return {
    id: utils.generateId('metric'),
    name: metricType.name,
    value: metricType.format(rawValue),
    raw_value: rawValue,
    unit: metricType.unit,
    service: service,
    timestamp: new Date().toISOString()
  };
};

const generateLog = () => {
  const service = utils.randomItem(config.services);
  const levels = ['INFO', 'WARN', 'ERROR', 'DEBUG'];
  const level = utils.randomItem(levels);
  
  return {
    id: utils.generateId('log'),
    timestamp: new Date().toISOString(),
    level,
    message: `Sample log message from ${service}`,
    service,
    metadata: {
      host: `${service}-${Math.floor(Math.random() * 10)}`,
      pod: `${service}-pod-${Math.floor(Math.random() * 100)}`,
      namespace: 'default'
    }
  };
};

const generateDeployment = () => {
  const service = utils.randomItem(config.services);
  const statuses = ['deployed', 'failed', 'in_progress', 'cancelled'];
  const status = utils.randomItem(statuses);
  
  return {
    id: utils.generateId('deploy'),
    service,
    version: `v${utils.randomNumber(1, 5)}.${utils.randomNumber(0, 15)}.${utils.randomNumber(0, 20)}`,
    status,
    timestamp: new Date().toISOString(),
    user: utils.randomItem(['system', 'admin', 'ci-pipeline', 'jenkins', 'github-actions']),
    environment: utils.randomItem(['production', 'staging', 'development', 'testing'])
  };
};

const generateAgentStatus = () => {
  const agents = [
    { id: 'metric-agent', name: 'Metric Agent' },
    { id: 'log-agent', name: 'Log Agent' },
    { id: 'deployment-agent', name: 'Deployment Agent' },
    { id: 'tracing-agent', name: 'Tracing Agent' },
    { id: 'root-cause-agent', name: 'Root Cause Agent' },
    { id: 'notification-agent', name: 'Notification Agent' },
    { id: 'postmortem-agent', name: 'Postmortem Agent' },
    { id: 'runbook-agent', name: 'Runbook Agent' }
  ];
  const agent = utils.randomItem(agents);
  const statuses = ['active', 'degraded', 'inactive'];
  
  return {
    id: agent.id,
    name: agent.name,
    status: utils.randomItem(statuses),
    timestamp: new Date().toISOString(),
    version: `v${utils.randomNumber(1, 3)}.${utils.randomNumber(0, 10)}.${utils.randomNumber(0, 20)}`,
    uptime_seconds: utils.randomNumber(60, 86400)
  };
};

const generateAlert = () => {
  const service = utils.randomItem(config.services);
  const severities = ['critical', 'warning', 'info'];
  const statuses = ['open', 'acknowledged', 'in_progress', 'resolved'];
  
  return {
    id: utils.generateId('alert'),
    labels: {
      alertname: 'TestAlert',
      service,
      severity: utils.randomItem(severities),
      instance: `${service}-${utils.randomNumber(1, 5)}`,
      namespace: 'default'
    },
    annotations: {
      summary: 'Test alert for data generation',
      description: `This is a test alert for ${service}`,
      value: `${utils.randomNumber(50, 100)}%`,
      threshold: '50%'
    },
    startsAt: new Date(Date.now() - utils.randomNumber(5, 60) * 60 * 1000).toISOString(),
    endsAt: Math.random() > 0.3 ? new Date().toISOString() : null,
    status: utils.randomItem(statuses)
  };
};

const generateRunbook = () => {
  const service = utils.randomItem(config.services);
  
  return {
    id: utils.generateId('rb'),
    title: `Test Runbook for ${service}`,
    service,
    steps: [
      `Check ${service} logs for errors`,
      `Verify ${service} is running`,
      `Check system resources`,
      `Restart ${service} if necessary`
    ],
    createdAt: new Date(Date.now() - utils.randomNumber(1, 90) * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date().toISOString()
  };
};

// Map of component names to generator functions
const generators = {
  metrics: generateMetric,
  logs: generateLog,
  deployments: generateDeployment,
  agents: generateAgentStatus,
  alerts: generateAlert,
  runbooks: generateRunbook
};

/**
 * Main function
 */
async function main() {
  console.log('Test Data Generator for Observability Agent UI');
  console.log('--------------------------------------------');
  console.log(`Component: ${config.component}`);
  console.log(`Count: ${config.count}`);
  console.log(`Services: ${config.services.join(', ')}`);
  console.log('--------------------------------------------');
  
  if (config.component === 'all') {
    // Generate data for all components
    for (const [component, generator] of Object.entries(generators)) {
      console.log(`\n=== ${component.toUpperCase()} ===`);
      for (let i = 0; i < config.count; i++) {
        const data = generator();
        console.log(JSON.stringify(data, null, 2));
      }
    }
  } else if (generators[config.component]) {
    // Generate data for the specified component
    const generator = generators[config.component];
    console.log(`\n=== ${config.component.toUpperCase()} ===`);
    for (let i = 0; i < config.count; i++) {
      const data = generator();
      console.log(JSON.stringify(data, null, 2));
    }
  } else {
    console.error(`Unknown component: ${config.component}`);
    console.error(`Available components: ${Object.keys(generators).join(', ')}`);
    process.exit(1);
  }
}

// Run the main function
main().catch(err => {
  console.error(`Fatal error: ${err.message}`);
  process.exit(1);
});
