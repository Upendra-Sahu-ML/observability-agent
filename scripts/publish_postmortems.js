#!/usr/bin/env node
/**
 * Postmortem Data Generator for Observability Agent UI
 * 
 * This script generates and publishes sample postmortem data to NATS for the UI to consume.
 * 
 * Usage:
 *   node publish_postmortems.js [options]
 * 
 * Options:
 *   --nats-url=<url>       NATS server URL (default: nats://localhost:4222)
 *   --count=<number>       Number of postmortems to generate (default: 5)
 *   --interval=<ms>        Interval between publications in ms (default: 3000)
 *   --continuous           Run continuously (default: false)
 *   --services=<list>      Comma-separated list of services (default: payment-service,order-service,inventory-service,api-gateway)
 * 
 * Example:
 *   node publish_postmortems.js --nats-url=nats://localhost:4222 --count=3
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
  count: parseInt(args['count'] || '5'),
  interval: parseInt(args['interval'] || '3000'),
  continuous: args['continuous'] === true,
  services: (args['services'] || 'payment-service,order-service,inventory-service,api-gateway').split(',')
};

// Postmortem statuses
const statuses = ['draft', 'in_progress', 'review', 'completed'];

// Postmortem templates by service
const postmortemTemplates = {
  'payment-service': [
    {
      title: 'Payment Service Outage - Database Connection Pool Exhaustion',
      summary: 'The payment service experienced an outage due to database connection pool exhaustion.',
      rootCause: 'Database connection pool exhaustion due to traffic spike.',
      impact: 'Approximately 500 users were unable to complete payments for 15 minutes.',
      resolution: 'Increased connection pool size and implemented better connection management.',
      actionItems: [
        'Implement connection pool monitoring',
        'Add auto-scaling for the payment service',
        'Improve error handling for database connection failures'
      ]
    },
    {
      title: 'Payment Gateway Integration Failure',
      summary: 'The payment service was unable to process transactions due to payment gateway integration issues.',
      rootCause: 'API changes in the payment gateway were not properly handled by our integration.',
      impact: 'All payment transactions failed for approximately 30 minutes.',
      resolution: 'Updated the payment gateway integration code to handle the new API format.',
      actionItems: [
        'Implement better monitoring for payment gateway API changes',
        'Add comprehensive integration tests for payment gateway',
        'Set up a staging environment for payment gateway testing'
      ]
    }
  ],
  'order-service': [
    {
      title: 'Order Service Performance Degradation',
      summary: 'The order service experienced significant performance degradation affecting order processing.',
      rootCause: 'Memory leak in the order processing component caused by improper resource cleanup.',
      impact: 'Order processing times increased by 300% for approximately 2 hours.',
      resolution: 'Fixed memory leak by properly closing resources and implemented memory usage monitoring.',
      actionItems: [
        'Add memory usage alerts',
        'Implement regular heap dump analysis',
        'Review resource cleanup in all service components'
      ]
    },
    {
      title: 'Order Database Index Corruption',
      summary: 'The order service database experienced index corruption leading to slow queries.',
      rootCause: 'Database maintenance job failure caused index corruption.',
      impact: 'Order lookups and creation were delayed by up to 1 minute for 4 hours.',
      resolution: 'Rebuilt database indexes and fixed the maintenance job.',
      actionItems: [
        'Implement index health monitoring',
        'Add alerts for maintenance job failures',
        'Create runbook for index rebuilding procedure'
      ]
    }
  ],
  'inventory-service': [
    {
      title: 'Inventory Service Data Inconsistency',
      summary: 'The inventory service reported incorrect stock levels causing order fulfillment issues.',
      rootCause: 'Race condition in concurrent inventory updates led to data inconsistency.',
      impact: 'Approximately 200 orders were affected by incorrect inventory data over 3 hours.',
      resolution: 'Implemented proper locking mechanism for inventory updates and added consistency checks.',
      actionItems: [
        'Add inventory consistency validation job',
        'Implement transaction isolation for inventory updates',
        'Add monitoring for inventory discrepancies'
      ]
    },
    {
      title: 'Inventory Service High CPU Usage',
      summary: 'The inventory service experienced high CPU usage affecting response times.',
      rootCause: 'Inefficient query pattern causing excessive CPU usage during inventory checks.',
      impact: 'Inventory checks took up to 10 seconds instead of the normal 200ms for 1 hour.',
      resolution: 'Optimized query patterns and added database indexes to improve performance.',
      actionItems: [
        'Implement query performance monitoring',
        'Review and optimize all database queries',
        'Add CPU usage alerts for early detection'
      ]
    }
  ],
  'api-gateway': [
    {
      title: 'API Gateway Rate Limiting Misconfiguration',
      summary: 'The API gateway incorrectly rate-limited legitimate traffic causing service disruption.',
      rootCause: 'Configuration error in rate limiting settings after deployment.',
      impact: 'Approximately 30% of legitimate API requests were rejected for 45 minutes.',
      resolution: 'Fixed rate limiting configuration and implemented configuration validation.',
      actionItems: [
        'Add configuration validation in CI/CD pipeline',
        'Implement canary deployments for configuration changes',
        'Create automated tests for rate limiting behavior'
      ]
    },
    {
      title: 'API Gateway TLS Certificate Expiration',
      summary: 'The API gateway TLS certificate expired causing connection failures.',
      rootCause: 'Certificate renewal automation failed and monitoring did not alert properly.',
      impact: 'All HTTPS connections to the API failed for 20 minutes.',
      resolution: 'Manually renewed certificate and fixed the renewal automation.',
      actionItems: [
        'Implement certificate expiration monitoring with longer lead time',
        'Add redundancy to certificate renewal process',
        'Create incident response runbook for certificate issues'
      ]
    }
  ]
};

/**
 * Generate a random date in the past (up to 30 days ago)
 * @returns {Date} - Random date in the past
 */
function randomPastDate() {
  const now = new Date();
  const thirtyDaysAgo = new Date(now.getTime() - (30 * 24 * 60 * 60 * 1000));
  return new Date(thirtyDaysAgo.getTime() + Math.random() * (now.getTime() - thirtyDaysAgo.getTime()));
}

/**
 * Generate a random postmortem
 * @returns {Object} - Postmortem data
 */
function generatePostmortem() {
  const service = utils.randomItem(config.services);
  const templates = postmortemTemplates[service] || [];
  
  if (templates.length === 0) {
    // Fallback if no templates for this service
    return {
      id: utils.generateId('pm'),
      alertId: utils.generateId('alert'),
      title: `${service} Incident - ${new Date().toLocaleDateString()}`,
      status: utils.randomItem(statuses),
      createdAt: randomPastDate().toISOString(),
      summary: `The ${service} experienced an incident that required investigation.`,
      impact: 'Impact details not available.',
      rootCause: 'Root cause analysis not completed.',
      resolution: 'Resolution details not available.',
      actionItems: ['Complete root cause analysis', 'Document resolution steps'],
      service
    };
  }
  
  const template = utils.randomItem(templates);
  const createdAt = randomPastDate();
  
  // Generate a random status based on age (older postmortems more likely to be completed)
  const daysSinceCreation = (Date.now() - createdAt.getTime()) / (24 * 60 * 60 * 1000);
  let status;
  if (daysSinceCreation > 20) {
    status = 'completed';
  } else if (daysSinceCreation > 10) {
    status = Math.random() < 0.7 ? 'completed' : 'review';
  } else if (daysSinceCreation > 5) {
    status = utils.randomItem(['in_progress', 'review', 'completed']);
  } else {
    status = utils.randomItem(['draft', 'in_progress', 'review']);
  }
  
  // Generate markdown content
  const content = `# ${template.title}

## Incident Summary
- **Date**: ${createdAt.toLocaleDateString()}
- **Duration**: ${utils.randomNumber(15, 240)} minutes
- **Impact**: ${template.impact}
- **Status**: ${status}

## Root Cause
${template.rootCause}

## Timeline
${generateTimeline(createdAt)}

## Resolution
${template.resolution}

## Action Items
${template.actionItems.map(item => `- ${item}`).join('\n')}

## Lessons Learned
1. Improved monitoring is needed for early detection
2. Better automation could have prevented this issue
3. Documentation needs to be updated with troubleshooting steps
`;
  
  return {
    id: utils.generateId('pm'),
    alertId: utils.generateId('alert'),
    title: template.title,
    status,
    createdAt: createdAt.toISOString(),
    summary: template.summary,
    impact: template.impact,
    rootCause: template.rootCause,
    resolution: template.resolution,
    actionItems: template.actionItems,
    content,
    service,
    author: utils.randomItem(['system', 'admin', 'sre-team', 'devops', 'incident-manager'])
  };
}

/**
 * Generate a random timeline for the postmortem
 * @param {Date} startDate - Incident start date
 * @returns {string} - Timeline in markdown format
 */
function generateTimeline(startDate) {
  const timeline = [];
  const startTime = startDate.getTime();
  
  // Detection (0-5 minutes after start)
  const detectionTime = new Date(startTime + utils.randomNumber(0, 5) * 60000);
  timeline.push(`- **${detectionTime.toLocaleTimeString()}**: Incident detected via monitoring alert`);
  
  // Acknowledgement (1-10 minutes after detection)
  const ackTime = new Date(detectionTime.getTime() + utils.randomNumber(1, 10) * 60000);
  timeline.push(`- **${ackTime.toLocaleTimeString()}**: On-call engineer acknowledged the alert`);
  
  // Investigation (5-20 minutes after acknowledgement)
  const investigationTime = new Date(ackTime.getTime() + utils.randomNumber(5, 20) * 60000);
  timeline.push(`- **${investigationTime.toLocaleTimeString()}**: Root cause identified`);
  
  // Mitigation (5-30 minutes after investigation)
  const mitigationTime = new Date(investigationTime.getTime() + utils.randomNumber(5, 30) * 60000);
  timeline.push(`- **${mitigationTime.toLocaleTimeString()}**: Mitigation steps implemented`);
  
  // Resolution (5-15 minutes after mitigation)
  const resolutionTime = new Date(mitigationTime.getTime() + utils.randomNumber(5, 15) * 60000);
  timeline.push(`- **${resolutionTime.toLocaleTimeString()}**: Service returned to normal operation`);
  
  return timeline.join('\n');
}

/**
 * Main function
 */
async function main() {
  console.log('Postmortem Data Generator for Observability Agent UI');
  console.log('--------------------------------------------------');
  console.log(`NATS URL: ${config.natsUrl}`);
  console.log(`Count: ${config.count}`);
  console.log(`Interval: ${config.interval}ms`);
  console.log(`Continuous: ${config.continuous}`);
  console.log(`Services: ${config.services.join(', ')}`);
  console.log('--------------------------------------------------');
  
  try {
    // Connect to NATS
    const { nc, js } = await utils.connectToNATS(config.natsUrl);
    
    // Ensure POSTMORTEMS stream exists
    await utils.ensureStream(js, 'POSTMORTEMS', ['postmortems.*']);
    
    // Generate and publish postmortems
    let count = 0;
    
    async function publishPostmortem() {
      if (!config.continuous && count >= config.count) {
        console.log(`Published ${count} postmortems. Done.`);
        await nc.drain();
        process.exit(0);
      }
      
      const postmortem = generatePostmortem();
      const subject = `postmortems.${postmortem.service.replace(/-/g, '_')}`;
      
      const success = await utils.publishData(js, subject, postmortem);
      
      if (success) {
        count++;
        console.log(`[${count}] Published postmortem: ${postmortem.title} (${postmortem.status})`);
      }
      
      if (config.continuous || count < config.count) {
        setTimeout(publishPostmortem, config.interval);
      } else {
        console.log(`Published ${count} postmortems. Done.`);
        await nc.drain();
        process.exit(0);
      }
    }
    
    // Start publishing
    publishPostmortem();
    
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
