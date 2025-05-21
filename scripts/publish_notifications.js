#!/usr/bin/env node
/**
 * Notification Data Generator for Observability Agent UI
 * 
 * This script generates and publishes sample notification data to NATS for the UI to consume.
 * 
 * Usage:
 *   node publish_notifications.js [options]
 * 
 * Options:
 *   --nats-url=<url>       NATS server URL (default: nats://localhost:4222)
 *   --count=<number>       Number of notifications to generate (default: 12)
 *   --interval=<ms>        Interval between publications in ms (default: 2000)
 *   --continuous           Run continuously (default: false)
 *   --services=<list>      Comma-separated list of services (default: payment-service,order-service,inventory-service,api-gateway)
 * 
 * Example:
 *   node publish_notifications.js --nats-url=nats://localhost:4222 --count=10
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
  count: parseInt(args['count'] || '12'),
  interval: parseInt(args['interval'] || '2000'),
  continuous: args['continuous'] === true,
  services: (args['services'] || 'payment-service,order-service,inventory-service,api-gateway').split(',')
};

// Notification channels
const channels = [
  { name: 'slack', recipients: ['#incidents', '#alerts', '#ops', '#dev-team'] },
  { name: 'email', recipients: ['oncall@example.com', 'ops-team@example.com', 'dev-team@example.com', 'sre@example.com'] },
  { name: 'pagerduty', recipients: ['primary-oncall', 'secondary-oncall', 'manager-escalation'] },
  { name: 'webhook', recipients: ['monitoring-system', 'ticketing-system', 'status-page'] },
  { name: 'sms', recipients: ['+1234567890', '+0987654321'] }
];

// Notification statuses
const statuses = [
  { status: 'sent', weight: 80 },
  { status: 'pending', weight: 10 },
  { status: 'failed', weight: 10 }
];

// Alert templates by service
const alertTemplates = {
  'payment-service': [
    'High CPU usage detected in payment-service',
    'Memory leak detected in payment-service',
    'Database connection pool exhaustion in payment-service',
    'Payment gateway timeout detected',
    'High error rate in payment processing'
  ],
  'order-service': [
    'High latency detected in order-service',
    'Order processing queue backlog detected',
    'Database query timeout in order-service',
    'Order service instance restarting frequently',
    'High memory usage in order-service'
  ],
  'inventory-service': [
    'Inventory database connection issues detected',
    'High disk usage on inventory-service',
    'Inventory update failures detected',
    'Slow inventory queries affecting performance',
    'Inventory service health check failing'
  ],
  'api-gateway': [
    'High request rate detected at api-gateway',
    'Increased error responses from api-gateway',
    'API gateway rate limiting triggered',
    'Slow response time from api-gateway',
    'API gateway connection pool exhaustion'
  ]
};

/**
 * Select a notification status based on weights
 * @returns {string} - Notification status
 */
function selectStatus() {
  const totalWeight = statuses.reduce((sum, status) => sum + status.weight, 0);
  let random = Math.random() * totalWeight;
  
  for (const status of statuses) {
    if (random < status.weight) {
      return status.status;
    }
    random -= status.weight;
  }
  
  return 'sent'; // Default fallback
}

/**
 * Generate a random notification
 * @returns {Object} - Notification data
 */
function generateNotification() {
  const service = utils.randomItem(config.services);
  const alertId = utils.generateId('alert');
  const channel = utils.randomItem(channels);
  const recipient = utils.randomItem(channel.recipients);
  const status = selectStatus();
  
  // Get alert templates for this service, or use a generic template
  const templates = alertTemplates[service] || [`Alert for ${service}`];
  const message = utils.randomItem(templates);
  
  const notification = {
    id: utils.generateId('notif'),
    alertId,
    channel: channel.name,
    recipient,
    message,
    status,
    timestamp: new Date().toISOString(),
    service,
    metadata: {
      alert_severity: utils.randomItem(['critical', 'warning', 'info']),
      notification_type: utils.randomItem(['alert', 'recovery', 'reminder', 'escalation']),
      attempt: status === 'failed' ? utils.randomNumber(1, 3) : 1
    }
  };
  
  // Add failure reason for failed notifications
  if (status === 'failed') {
    notification.failure_reason = utils.randomItem([
      'Service unavailable',
      'Rate limit exceeded',
      'Invalid recipient',
      'Authentication failure',
      'Network timeout'
    ]);
  }
  
  return notification;
}

/**
 * Main function
 */
async function main() {
  console.log('Notification Data Generator for Observability Agent UI');
  console.log('----------------------------------------------------');
  console.log(`NATS URL: ${config.natsUrl}`);
  console.log(`Count: ${config.count}`);
  console.log(`Interval: ${config.interval}ms`);
  console.log(`Continuous: ${config.continuous}`);
  console.log(`Services: ${config.services.join(', ')}`);
  console.log('----------------------------------------------------');
  
  try {
    // Connect to NATS
    const { nc, js } = await utils.connectToNATS(config.natsUrl);
    
    // Ensure NOTIFICATIONS stream exists
    await utils.ensureStream(js, 'NOTIFICATIONS', ['notifications.*']);
    
    // Generate and publish notifications
    let count = 0;
    
    async function publishNotification() {
      if (!config.continuous && count >= config.count) {
        console.log(`Published ${count} notifications. Done.`);
        await nc.drain();
        process.exit(0);
      }
      
      const notification = generateNotification();
      const subject = `notifications.${notification.channel}`;
      
      const success = await utils.publishData(js, subject, notification);
      
      if (success) {
        count++;
        console.log(`[${count}] Published notification: ${notification.message} via ${notification.channel} to ${notification.recipient} (${notification.status})`);
        if (notification.failure_reason) {
          console.log(`    Failure reason: ${notification.failure_reason}`);
        }
      }
      
      if (config.continuous || count < config.count) {
        setTimeout(publishNotification, config.interval);
      } else {
        console.log(`Published ${count} notifications. Done.`);
        await nc.drain();
        process.exit(0);
      }
    }
    
    // Start publishing
    publishNotification();
    
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
