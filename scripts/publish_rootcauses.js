#!/usr/bin/env node
/**
 * Root Cause Analysis Data Generator for Observability Agent UI
 *
 * This script generates and publishes sample root cause analysis data to NATS for the UI to consume.
 *
 * Usage:
 *   node publish_rootcauses.js [options]
 *
 * Options:
 *   --nats-url=<url>       NATS server URL (default: nats://localhost:4222)
 *   --count=<number>       Number of root causes to generate (default: 8)
 *   --interval=<ms>        Interval between publications in ms (default: 3000)
 *   --continuous           Run continuously (default: false)
 *   --services=<list>      Comma-separated list of services (default: payment-service,order-service,inventory-service,api-gateway)
 *
 * Example:
 *   node publish_rootcauses.js --nats-url=nats://localhost:4222 --count=5
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
  interval: parseInt(args['interval'] || '3000'),
  continuous: args['continuous'] === true,
  services: (args['services'] || 'payment-service,order-service,inventory-service,api-gateway').split(',')
};

// Root cause templates by service
const rootCauseTemplates = {
  'payment-service': [
    {
      cause: 'Database connection pool exhaustion',
      details: 'The payment service experienced high traffic which exhausted the database connection pool.',
      confidence: 0.92
    },
    {
      cause: 'Payment gateway timeout',
      details: 'The external payment gateway is responding slowly, causing timeouts in the payment service.',
      confidence: 0.85
    },
    {
      cause: 'Memory leak in payment processing',
      details: 'A memory leak was detected in the payment processing component, causing gradual performance degradation.',
      confidence: 0.78
    },
    {
      cause: 'High CPU usage due to inefficient query',
      details: 'An inefficient database query in the payment service is causing high CPU usage.',
      confidence: 0.88
    }
  ],
  'order-service': [
    {
      cause: 'Deadlock in order processing',
      details: 'A deadlock was detected in the order processing workflow, causing orders to stall.',
      confidence: 0.91
    },
    {
      cause: 'Disk I/O bottleneck',
      details: 'High disk I/O is causing slow order processing due to log file growth.',
      confidence: 0.82
    },
    {
      cause: 'Network latency to inventory service',
      details: 'Increased network latency between order service and inventory service is causing delays.',
      confidence: 0.79
    },
    {
      cause: 'Cache eviction rate too high',
      details: 'The order service cache is experiencing a high eviction rate, causing increased database load.',
      confidence: 0.86
    }
  ],
  'inventory-service': [
    {
      cause: 'Database index fragmentation',
      details: 'Fragmented database indexes in the inventory database are causing slow queries.',
      confidence: 0.89
    },
    {
      cause: 'Resource contention',
      details: 'Multiple concurrent inventory updates are causing resource contention.',
      confidence: 0.84
    },
    {
      cause: 'Slow disk performance',
      details: 'The inventory service is experiencing slow disk performance affecting database operations.',
      confidence: 0.77
    },
    {
      cause: 'Memory pressure',
      details: 'High memory usage in the inventory service is causing frequent garbage collection pauses.',
      confidence: 0.81
    }
  ],
  'api-gateway': [
    {
      cause: 'Rate limiting misconfiguration',
      details: 'The API gateway rate limiting is misconfigured, causing legitimate requests to be rejected.',
      confidence: 0.93
    },
    {
      cause: 'TLS handshake failures',
      details: 'Intermittent TLS handshake failures are causing connection issues to the API gateway.',
      confidence: 0.87
    },
    {
      cause: 'Routing table corruption',
      details: 'The API gateway routing table is corrupted, causing requests to be misrouted.',
      confidence: 0.83
    },
    {
      cause: 'Load balancer health check failure',
      details: 'The load balancer health checks are failing, causing reduced capacity in the API gateway.',
      confidence: 0.90
    }
  ]
};

/**
 * Generate a random root cause analysis
 * @returns {Object} - Root cause analysis data
 */
function generateRootCause() {
  const service = utils.randomItem(config.services);
  const templates = rootCauseTemplates[service] || [];

  if (templates.length === 0) {
    // Fallback if no templates for this service
    return {
      id: utils.generateId('rc'),
      alertId: utils.generateId('alert'),
      service,
      cause: 'Unknown issue',
      confidence: 0.5,
      timestamp: new Date().toISOString(),
      details: 'No specific details available for this service.'
    };
  }

  const template = utils.randomItem(templates);

  // Add some randomness to confidence
  const confidenceVariation = (Math.random() * 0.1) - 0.05; // -0.05 to +0.05
  const confidence = Math.max(0, Math.min(1, template.confidence + confidenceVariation));

  return {
    id: utils.generateId('rc'),
    alertId: utils.generateId('alert'),
    service,
    cause: template.cause,
    confidence: parseFloat(confidence.toFixed(2)),
    timestamp: new Date().toISOString(),
    details: template.details,
    metrics: {
      affected_requests: utils.randomNumber(10, 5000),
      duration_seconds: utils.randomNumber(30, 1800),
      impact_score: parseFloat((Math.random() * 10).toFixed(1))
    },
    recommended_actions: [
      `Investigate ${service} logs for errors related to "${template.cause}"`,
      `Check ${service} resource utilization`,
      `Verify ${service} configuration settings`
    ]
  };
}

/**
 * Main function
 */
async function main() {
  console.log('Root Cause Analysis Data Generator for Observability Agent UI');
  console.log('----------------------------------------------------------');
  console.log(`NATS URL: ${config.natsUrl}`);
  console.log(`Count: ${config.count}`);
  console.log(`Interval: ${config.interval}ms`);
  console.log(`Continuous: ${config.continuous}`);
  console.log(`Services: ${config.services.join(', ')}`);
  console.log('----------------------------------------------------------');

  try {
    // Connect to NATS
    const { nc, js } = await utils.connectToNATS(config.natsUrl);

    // Ensure ROOT_CAUSE stream exists
    await utils.ensureStream(js, 'ROOT_CAUSE', ['root_cause_analysis', 'root_cause_result', 'rootcause', 'rootcause.*']);

    // Generate and publish root causes
    let count = 0;

    async function publishRootCause() {
      if (!config.continuous && count >= config.count) {
        console.log(`Published ${count} root causes. Done.`);
        await nc.drain();
        process.exit(0);
      }

      const rootCause = generateRootCause();
      const subject = `rootcause.${rootCause.service.replace(/-/g, '_')}`;

      const success = await utils.publishData(js, subject, rootCause);

      if (success) {
        count++;
        console.log(`[${count}] Published root cause: ${rootCause.cause} (${rootCause.service}, confidence: ${rootCause.confidence})`);
      }

      if (config.continuous || count < config.count) {
        setTimeout(publishRootCause, config.interval);
      } else {
        console.log(`Published ${count} root causes. Done.`);
        await nc.drain();
        process.exit(0);
      }
    }

    // Start publishing
    publishRootCause();

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
