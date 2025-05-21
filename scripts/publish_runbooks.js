#!/usr/bin/env node
/**
 * Runbook Data Generator for Observability Agent UI
 *
 * This script generates and publishes sample runbook data to NATS for the UI to consume.
 *
 * Usage:
 *   node publish_runbooks.js [options]
 *
 * Options:
 *   --nats-url=<url>       NATS server URL (default: nats://localhost:4222)
 *   --count=<number>       Number of runbooks to generate (default: 8)
 *   --interval=<ms>        Interval between publications in ms (default: 2000)
 *   --continuous           Run continuously (default: false)
 *   --services=<list>      Comma-separated list of services (default: payment-service,order-service,inventory-service,api-gateway)
 *
 * Example:
 *   node publish_runbooks.js --nats-url=nats://localhost:4222 --count=5
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
  count: parseInt(args['count'] || '8'),
  interval: parseInt(args['interval'] || '2000'),
  continuous: args['continuous'] === true,
  services: (args['services'] || 'payment-service,order-service,inventory-service,api-gateway').split(',')
};

// Runbook templates by service
const runbookTemplates = {
  'payment-service': [
    {
      title: 'Database Connection Issues',
      steps: [
        'Check database connection pool settings',
        'Verify database server is running',
        'Check for network connectivity issues',
        'Restart the payment service if necessary'
      ],
      description: 'This runbook helps diagnose and resolve database connection issues in the payment service.'
    },
    {
      title: 'Payment Gateway Timeout',
      steps: [
        'Check payment gateway status page',
        'Verify API credentials are valid',
        'Test connection to payment gateway',
        'Check network latency to payment gateway',
        'Implement fallback payment processor if necessary'
      ],
      description: 'Follow these steps when the payment gateway is timing out or unreachable.'
    },
    {
      title: 'High CPU Usage Remediation',
      steps: [
        'Identify processes consuming high CPU',
        'Check for recent code deployments',
        'Look for unusual traffic patterns',
        'Scale up the service horizontally if needed',
        'Restart problematic instances'
      ],
      description: 'Use this runbook when the payment service is experiencing high CPU usage.'
    }
  ],
  'order-service': [
    {
      title: 'Order Processing Queue Backlog',
      steps: [
        'Check current queue depth',
        'Verify order processors are running',
        'Look for errors in order processing logs',
        'Scale up order processors if needed',
        'Implement rate limiting if necessary'
      ],
      description: 'This runbook addresses a backlog in the order processing queue.'
    },
    {
      title: 'Memory Leak Remediation',
      steps: [
        'Take heap dump of the affected service',
        'Analyze memory usage patterns',
        'Identify objects with unusual retention',
        'Apply fix to release references properly',
        'Restart the service with the fix'
      ],
      description: 'Follow these steps when the order service is experiencing memory leaks.'
    }
  ],
  'inventory-service': [
    {
      title: 'Inventory Data Inconsistency',
      steps: [
        'Run inventory consistency check',
        'Identify discrepancies between actual and reported inventory',
        'Pause inventory updates temporarily',
        'Apply corrections to inventory data',
        'Resume normal operation and monitor'
      ],
      description: 'Use this runbook to resolve inconsistencies in inventory data.'
    },
    {
      title: 'Slow Inventory Queries',
      steps: [
        'Identify slow-running queries',
        'Check database index health',
        'Analyze query execution plans',
        'Optimize problematic queries',
        'Add or update indexes if necessary'
      ],
      description: 'Follow these steps when inventory queries are running slowly.'
    }
  ],
  'api-gateway': [
    {
      title: 'High Latency Troubleshooting',
      steps: [
        'Check system load on API gateway instances',
        'Verify downstream service health',
        'Look for network bottlenecks',
        'Check for recent configuration changes',
        'Scale up the gateway if necessary'
      ],
      description: 'This runbook helps diagnose and resolve high latency issues in the API gateway.'
    },
    {
      title: 'Rate Limiting Configuration',
      steps: [
        'Review current rate limiting settings',
        'Analyze traffic patterns',
        'Identify legitimate vs. abusive traffic',
        'Adjust rate limits as needed',
        'Implement IP-based blocking for abusive clients'
      ],
      description: 'Use this runbook to configure rate limiting in the API gateway.'
    }
  ]
};

/**
 * Generate a random date in the past (up to 90 days ago)
 * @returns {Date} - Random date in the past
 */
function randomPastDate() {
  const now = new Date();
  const ninetyDaysAgo = new Date(now.getTime() - (90 * 24 * 60 * 60 * 1000));
  return new Date(ninetyDaysAgo.getTime() + Math.random() * (now.getTime() - ninetyDaysAgo.getTime()));
}

/**
 * Generate a random runbook
 * @returns {Object} - Runbook data
 */
function generateRunbook() {
  const service = utils.randomItem(config.services);
  const templates = runbookTemplates[service] || [];

  if (templates.length === 0) {
    // Fallback if no templates for this service
    return {
      id: utils.generateId('rb'),
      title: `${service} Troubleshooting`,
      service,
      steps: [
        `Check ${service} logs for errors`,
        `Verify ${service} is running`,
        `Check system resources`,
        `Restart ${service} if necessary`
      ],
      createdAt: randomPastDate().toISOString(),
      updatedAt: new Date().toISOString(),
      description: `Basic troubleshooting steps for ${service}.`
    };
  }

  const template = utils.randomItem(templates);
  const createdAt = randomPastDate();

  // Generate markdown content
  const content = `# ${template.title}

## Description
${template.description}

## Steps
${template.steps.map((step, index) => `${index + 1}. ${step}`).join('\n')}

## Additional Information
- **Service**: ${service}
- **Created**: ${createdAt.toLocaleDateString()}
- **Last Updated**: ${new Date().toLocaleDateString()}
- **Author**: ${utils.randomItem(['system', 'admin', 'sre-team', 'devops'])}

## Related Resources
- [Service Documentation](https://example.com/docs/${service})
- [Monitoring Dashboard](https://example.com/dashboard/${service})
`;

  return {
    id: utils.generateId('rb'),
    title: template.title,
    service,
    steps: template.steps,
    content,
    createdAt: createdAt.toISOString(),
    updatedAt: new Date().toISOString(),
    author: utils.randomItem(['system', 'admin', 'sre-team', 'devops']),
    tags: ['troubleshooting', service, ...template.title.toLowerCase().split(' ')]
  };
}

/**
 * Main function
 */
async function main() {
  console.log('Runbook Data Generator for Observability Agent UI');
  console.log('-----------------------------------------------');
  console.log(`NATS URL: ${config.natsUrl}`);
  console.log(`Count: ${config.count}`);
  console.log(`Interval: ${config.interval}ms`);
  console.log(`Continuous: ${config.continuous}`);
  console.log(`Services: ${config.services.join(', ')}`);
  console.log('-----------------------------------------------');

  try {
    // Connect to NATS
    const { nc, js } = await utils.connectToNATS(config.natsUrl);

    // Ensure RUNBOOKS stream exists
    await utils.ensureStream(js, 'RUNBOOKS', ['runbooks', 'runbooks.*', 'runbook', 'runbook.data.*']);

    // Generate and publish runbooks
    let count = 0;

    async function publishRunbook() {
      if (!config.continuous && count >= config.count) {
        console.log(`Published ${count} runbooks. Done.`);
        await nc.drain();
        process.exit(0);
      }

      const runbook = generateRunbook();
      // Use runbook.data.* instead of runbook.* to avoid overlap with RUNBOOK_EXECUTIONS
      const subject = `runbook.data.${runbook.service.replace(/-/g, '_')}`;

      const success = await utils.publishData(js, subject, runbook);

      if (success) {
        count++;
        console.log(`[${count}] Published runbook: ${runbook.title} (${runbook.service}, ${runbook.steps.length} steps)`);
      }

      if (config.continuous || count < config.count) {
        setTimeout(publishRunbook, config.interval);
      } else {
        console.log(`Published ${count} runbooks. Done.`);
        await nc.drain();
        process.exit(0);
      }
    }

    // Start publishing
    publishRunbook();

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
