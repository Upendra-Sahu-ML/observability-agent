#!/usr/bin/env node
/**
 * Alert Data Generator for Observability Agent UI
 *
 * This script generates and publishes sample alert data to NATS for the UI to consume.
 *
 * Usage:
 *   node publish_alerts.js [options]
 *
 * Options:
 *   --nats-url=<url>       NATS server URL (default: nats://localhost:4222)
 *   --count=<number>       Number of alerts to generate (default: 15)
 *   --interval=<ms>        Interval between publications in ms (default: 2000)
 *   --continuous           Run continuously (default: false)
 *   --services=<list>      Comma-separated list of services (default: payment-service,order-service,inventory-service,api-gateway)
 *   --active-ratio=<float> Ratio of active to resolved alerts (default: 0.3)
 *
 * Example:
 *   node publish_alerts.js --nats-url=nats://localhost:4222 --count=10 --active-ratio=0.5
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
  natsUrl: args['nats-url'] || 'nats://localhost:4222',
  count: parseInt(args['count'] || '15'),
  interval: parseInt(args['interval'] || '2000'),
  continuous: args['continuous'] === true,
  services: (args['services'] || 'payment-service,order-service,inventory-service,api-gateway').split(','),
  activeRatio: parseFloat(args['active-ratio'] || '0.3')
};

// Alert templates by service
const alertTemplates = {
  'payment-service': [
    {
      alertname: 'HighCpuUsage',
      severity: 'warning',
      summary: 'High CPU usage detected',
      description: 'CPU usage above threshold for payment-service',
      value: () => `${utils.randomNumber(80, 95)}%`,
      threshold: '80%'
    },
    {
      alertname: 'HighMemoryUsage',
      severity: 'warning',
      summary: 'High memory usage detected',
      description: 'Memory usage above threshold for payment-service',
      value: () => `${utils.randomNumber(85, 98)}%`,
      threshold: '85%'
    },
    {
      alertname: 'DatabaseConnectionPoolExhaustion',
      severity: 'critical',
      summary: 'Database connection pool exhaustion',
      description: 'Connection pool utilization above threshold for payment-service',
      value: () => `${utils.randomNumber(90, 100)}%`,
      threshold: '90%'
    },
    {
      alertname: 'PaymentGatewayTimeout',
      severity: 'critical',
      summary: 'Payment gateway timeout',
      description: 'Payment gateway response time above threshold',
      value: () => `${utils.randomNumber(5000, 15000)}ms`,
      threshold: '5000ms'
    },
    {
      alertname: 'HighErrorRate',
      severity: 'critical',
      summary: 'High error rate detected',
      description: 'Error rate above threshold for payment-service',
      value: () => `${utils.randomNumber(5, 20)}%`,
      threshold: '5%'
    }
  ],
  'order-service': [
    {
      alertname: 'HighLatency',
      severity: 'warning',
      summary: 'High latency detected',
      description: 'Request latency above threshold for order-service',
      value: () => `${utils.randomNumber(1000, 5000)}ms`,
      threshold: '1000ms'
    },
    {
      alertname: 'OrderProcessingQueueBacklog',
      severity: 'warning',
      summary: 'Order processing queue backlog',
      description: 'Queue depth above threshold for order-service',
      value: () => `${utils.randomNumber(100, 500)} items`,
      threshold: '100 items'
    },
    {
      alertname: 'DatabaseQueryTimeout',
      severity: 'critical',
      summary: 'Database query timeout',
      description: 'Database queries timing out for order-service',
      value: () => `${utils.randomNumber(5, 20)} timeouts/minute`,
      threshold: '5 timeouts/minute'
    },
    {
      alertname: 'InstanceRestarting',
      severity: 'critical',
      summary: 'Service instance restarting frequently',
      description: 'Order service instance restarting too frequently',
      value: () => `${utils.randomNumber(3, 10)} restarts/hour`,
      threshold: '3 restarts/hour'
    }
  ],
  'inventory-service': [
    {
      alertname: 'DatabaseConnectionIssues',
      severity: 'critical',
      summary: 'Database connection issues',
      description: 'Inventory service unable to connect to database',
      value: () => `${utils.randomNumber(3, 10)} failures/minute`,
      threshold: '3 failures/minute'
    },
    {
      alertname: 'HighDiskUsage',
      severity: 'warning',
      summary: 'High disk usage',
      description: 'Disk usage above threshold for inventory-service',
      value: () => `${utils.randomNumber(85, 98)}%`,
      threshold: '85%'
    },
    {
      alertname: 'InventoryUpdateFailures',
      severity: 'warning',
      summary: 'Inventory update failures',
      description: 'Inventory updates failing above threshold',
      value: () => `${utils.randomNumber(5, 15)}%`,
      threshold: '5%'
    },
    {
      alertname: 'SlowInventoryQueries',
      severity: 'warning',
      summary: 'Slow inventory queries',
      description: 'Inventory queries taking longer than threshold',
      value: () => `${utils.randomNumber(500, 2000)}ms`,
      threshold: '500ms'
    }
  ],
  'api-gateway': [
    {
      alertname: 'HighRequestRate',
      severity: 'warning',
      summary: 'High request rate',
      description: 'Request rate above threshold for api-gateway',
      value: () => `${utils.randomNumber(1000, 5000)} req/s`,
      threshold: '1000 req/s'
    },
    {
      alertname: 'IncreasedErrorResponses',
      severity: 'critical',
      summary: 'Increased error responses',
      description: 'Error response rate above threshold for api-gateway',
      value: () => `${utils.randomNumber(5, 20)}%`,
      threshold: '5%'
    },
    {
      alertname: 'RateLimitingTriggered',
      severity: 'warning',
      summary: 'Rate limiting triggered',
      description: 'Rate limiting triggered for multiple clients',
      value: () => `${utils.randomNumber(10, 50)} clients`,
      threshold: '10 clients'
    },
    {
      alertname: 'SlowResponseTime',
      severity: 'warning',
      summary: 'Slow response time',
      description: 'Response time above threshold for api-gateway',
      value: () => `${utils.randomNumber(500, 2000)}ms`,
      threshold: '500ms'
    }
  ]
};

// Alert statuses for active alerts
const activeStatuses = ['open', 'acknowledged', 'in_progress'];

/**
 * Generate a random alert
 * @param {boolean} active - Whether to generate an active or resolved alert
 * @returns {Object} - Alert data
 */
function generateAlert(active) {
  const service = utils.randomItem(config.services);
  const templates = alertTemplates[service] || [];

  if (templates.length === 0) {
    // Fallback if no templates for this service
    return {
      id: utils.generateId('alert'),
      labels: {
        alertname: 'ServiceIssue',
        service,
        severity: 'warning',
        instance: `${service}-${utils.randomNumber(1, 5)}`,
        namespace: 'default'
      },
      annotations: {
        summary: `Issue detected in ${service}`,
        description: `An issue was detected in ${service}`,
        value: 'N/A',
        threshold: 'N/A'
      },
      startsAt: new Date(Date.now() - utils.randomNumber(5, 60) * 60 * 1000).toISOString(),
      endsAt: active ? null : new Date(Date.now() - utils.randomNumber(1, 10) * 60 * 1000).toISOString(),
      status: active ? utils.randomItem(activeStatuses) : 'resolved'
    };
  }

  const template = utils.randomItem(templates);
  const value = template.value();

  // Generate start time (between 1 hour ago and 5 minutes ago)
  const now = Date.now();
  const oneHourAgo = now - (60 * 60 * 1000);
  const fiveMinutesAgo = now - (5 * 60 * 1000);
  const startTime = new Date(utils.randomNumber(oneHourAgo, fiveMinutesAgo));

  // For resolved alerts, generate end time between start time and now
  const endTime = active ? null : new Date(startTime.getTime() + utils.randomNumber(5, 30) * 60 * 1000);

  return {
    id: utils.generateId('alert'),
    labels: {
      alertname: template.alertname,
      service,
      severity: template.severity,
      instance: `${service}-${utils.randomNumber(1, 5)}`,
      namespace: utils.randomItem(['default', 'prod', 'staging', 'dev'])
    },
    annotations: {
      summary: template.summary,
      description: template.description,
      value,
      threshold: template.threshold
    },
    startsAt: startTime.toISOString(),
    endsAt: endTime ? endTime.toISOString() : null,
    status: active ? utils.randomItem(activeStatuses) : 'resolved',
    generatorURL: `https://prometheus.example.com/graph?g0.expr=${encodeURIComponent(template.alertname)}&g0.tab=1`
  };
}

/**
 * Main function
 */
async function main() {
  console.log('Alert Data Generator for Observability Agent UI');
  console.log('---------------------------------------------');
  console.log(`NATS URL: ${config.natsUrl}`);
  console.log(`Count: ${config.count}`);
  console.log(`Interval: ${config.interval}ms`);
  console.log(`Continuous: ${config.continuous}`);
  console.log(`Services: ${config.services.join(', ')}`);
  console.log(`Active Alert Ratio: ${config.activeRatio}`);
  console.log('---------------------------------------------');

  try {
    // Connect to NATS
    const { nc, js } = await utils.connectToNATS(config.natsUrl);

    // Ensure ALERTS stream exists
    await utils.ensureStream(js, 'ALERTS', ['alerts', 'alerts.>']);

    // Generate and publish alerts
    let count = 0;

    async function publishAlert() {
      if (!config.continuous && count >= config.count) {
        console.log(`Published ${count} alerts. Done.`);
        await nc.drain();
        process.exit(0);
      }

      // Determine if this alert should be active based on the active ratio
      const isActive = Math.random() < config.activeRatio;

      const alert = generateAlert(isActive);
      const subject = `alerts.${alert.labels.service.replace(/-/g, '_')}.${alert.labels.alertname.toLowerCase()}`;

      const success = await utils.publishData(js, subject, alert);

      if (success) {
        count++;
        console.log(`[${count}] Published alert: ${alert.labels.alertname} (${alert.labels.service}, ${alert.status})`);
        console.log(`    ${alert.annotations.summary}: ${alert.annotations.value} (threshold: ${alert.annotations.threshold})`);
      }

      if (config.continuous || count < config.count) {
        setTimeout(publishAlert, config.interval);
      } else {
        console.log(`Published ${count} alerts. Done.`);
        await nc.drain();
        process.exit(0);
      }
    }

    // Start publishing
    publishAlert();

  } catch (error) {
    console.error(`Error: ${error.message}`);
    process.exit(1);
  }
}

// Run the main function
main().catch(err => {
  console.error(`Fatal error: ${err.message}`);
  process.exit(1);
});
