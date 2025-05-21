#!/usr/bin/env node
/**
 * Logs Data Generator for Observability Agent UI
 * 
 * This script generates and publishes sample logs data to NATS for the UI to consume.
 * 
 * Usage:
 *   node publish_logs.js [options]
 * 
 * Options:
 *   --nats-url=<url>       NATS server URL (default: nats://localhost:4222)
 *   --count=<number>       Number of logs to generate (default: 50)
 *   --interval=<ms>        Interval between publications in ms (default: 500)
 *   --continuous           Run continuously (default: false)
 *   --services=<list>      Comma-separated list of services (default: payment-service,order-service,inventory-service,api-gateway)
 * 
 * Example:
 *   node publish_logs.js --nats-url=nats://localhost:4222 --count=100 --continuous
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
  count: parseInt(args['count'] || '50'),
  interval: parseInt(args['interval'] || '500'),
  continuous: args['continuous'] === true,
  services: (args['services'] || 'payment-service,order-service,inventory-service,api-gateway').split(',')
};

// Log levels with their relative frequency (higher number = more frequent)
const logLevels = [
  { level: 'INFO', frequency: 70 },
  { level: 'WARN', frequency: 20 },
  { level: 'ERROR', frequency: 8 },
  { level: 'DEBUG', frequency: 2 }
];

// Log message templates by service and level
const logTemplates = {
  'payment-service': {
    'INFO': [
      'Payment processed successfully for order #ORDER_ID',
      'New payment method added for customer #CUSTOMER_ID',
      'Payment gateway connection established',
      'Payment service started successfully',
      'Processed AMOUNT payment for order #ORDER_ID'
    ],
    'WARN': [
      'Slow payment processing detected (AMOUNT ms)',
      'Payment retry attempt #RETRY_COUNT for order #ORDER_ID',
      'Payment gateway response time exceeding threshold',
      'High volume of payment requests detected'
    ],
    'ERROR': [
      'Payment processing failed for order #ORDER_ID: REASON',
      'Payment gateway connection failed: REASON',
      'Database query timeout during payment processing',
      'Invalid payment data received for order #ORDER_ID'
    ],
    'DEBUG': [
      'Payment request details: DETAILS',
      'Payment gateway response: RESPONSE',
      'Database query execution time: AMOUNT ms'
    ]
  },
  'order-service': {
    'INFO': [
      'Order #ORDER_ID created successfully',
      'Order #ORDER_ID status updated to STATUS',
      'Order service started successfully',
      'Processed ORDER_COUNT orders in the last minute'
    ],
    'WARN': [
      'Slow order processing detected (AMOUNT ms)',
      'High volume of orders detected',
      'Order #ORDER_ID has been pending for over 30 minutes',
      'Inventory check taking longer than expected'
    ],
    'ERROR': [
      'Failed to create order: REASON',
      'Order #ORDER_ID processing failed: REASON',
      'Database connection error during order creation',
      'Invalid order data received'
    ],
    'DEBUG': [
      'Order request details: DETAILS',
      'Order processing time: AMOUNT ms',
      'Database query execution time: AMOUNT ms'
    ]
  },
  'inventory-service': {
    'INFO': [
      'Inventory updated for product #PRODUCT_ID',
      'Inventory check completed for order #ORDER_ID',
      'Inventory service started successfully',
      'Stock level for product #PRODUCT_ID: AMOUNT units'
    ],
    'WARN': [
      'Low stock alert for product #PRODUCT_ID (AMOUNT units remaining)',
      'Slow inventory update detected (AMOUNT ms)',
      'Inventory database approaching capacity',
      'High volume of inventory checks detected'
    ],
    'ERROR': [
      'Failed to update inventory for product #PRODUCT_ID: REASON',
      'Inventory check failed for order #ORDER_ID: REASON',
      'Database connection error during inventory update',
      'Invalid inventory data received'
    ],
    'DEBUG': [
      'Inventory request details: DETAILS',
      'Inventory update time: AMOUNT ms',
      'Database query execution time: AMOUNT ms'
    ]
  },
  'api-gateway': {
    'INFO': [
      'Request processed: METHOD PATH',
      'Response sent: STATUS_CODE (AMOUNT ms)',
      'API gateway started successfully',
      'Processed REQUEST_COUNT requests in the last minute'
    ],
    'WARN': [
      'Slow response time for METHOD PATH (AMOUNT ms)',
      'Rate limiting applied to IP_ADDRESS',
      'High request volume detected',
      'Service dependency response time exceeding threshold'
    ],
    'ERROR': [
      'Request failed: METHOD PATH - STATUS_CODE',
      'Service dependency unavailable: SERVICE_NAME',
      'Invalid request data received for PATH',
      'Authentication failed for request to PATH'
    ],
    'DEBUG': [
      'Request details: DETAILS',
      'Response time: AMOUNT ms',
      'Authentication details: DETAILS'
    ]
  }
};

// Placeholder values to substitute in log messages
const placeholders = {
  'ORDER_ID': () => Math.floor(Math.random() * 100000),
  'CUSTOMER_ID': () => Math.floor(Math.random() * 50000),
  'PRODUCT_ID': () => Math.floor(Math.random() * 10000),
  'AMOUNT': () => Math.floor(Math.random() * 1000),
  'STATUS': () => utils.randomItem(['created', 'processing', 'shipped', 'delivered', 'cancelled']),
  'REASON': () => utils.randomItem(['timeout', 'invalid data', 'service unavailable', 'database error', 'network error']),
  'RETRY_COUNT': () => Math.floor(Math.random() * 5) + 1,
  'DETAILS': () => `{id: ${Math.floor(Math.random() * 10000)}, timestamp: "${new Date().toISOString()}"}`,
  'RESPONSE': () => `{status: "${utils.randomItem(['success', 'error', 'pending'])}", code: ${Math.floor(Math.random() * 100)}}`,
  'ORDER_COUNT': () => Math.floor(Math.random() * 100) + 1,
  'REQUEST_COUNT': () => Math.floor(Math.random() * 1000) + 1,
  'METHOD': () => utils.randomItem(['GET', 'POST', 'PUT', 'DELETE']),
  'PATH': () => utils.randomItem(['/api/orders', '/api/payments', '/api/products', '/api/customers', '/api/inventory']),
  'STATUS_CODE': () => utils.randomItem([200, 201, 400, 401, 403, 404, 500]),
  'IP_ADDRESS': () => `192.168.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`,
  'SERVICE_NAME': () => utils.randomItem(['payment-service', 'order-service', 'inventory-service', 'customer-service'])
};

/**
 * Select a log level based on frequency weights
 * @returns {string} - Log level
 */
function selectLogLevel() {
  const totalWeight = logLevels.reduce((sum, level) => sum + level.frequency, 0);
  let random = Math.random() * totalWeight;
  
  for (const level of logLevels) {
    if (random < level.frequency) {
      return level.level;
    }
    random -= level.frequency;
  }
  
  return 'INFO'; // Default fallback
}

/**
 * Replace placeholders in a message
 * @param {string} message - Message with placeholders
 * @returns {string} - Message with placeholders replaced
 */
function replacePlaceholders(message) {
  return message.replace(/([A-Z_]+)/g, (match) => {
    if (placeholders[match]) {
      return placeholders[match]();
    }
    return match;
  });
}

/**
 * Generate a random log entry
 * @returns {Object} - Log entry
 */
function generateLog() {
  const service = utils.randomItem(config.services);
  const level = selectLogLevel();
  
  // Get templates for this service and level, or use a generic template
  const templates = logTemplates[service]?.[level] || ['Log message from ${service}'];
  const messageTemplate = utils.randomItem(templates);
  const message = replacePlaceholders(messageTemplate);
  
  return {
    id: utils.generateId('log'),
    timestamp: new Date().toISOString(),
    level,
    message,
    service,
    metadata: {
      host: `${service}-${Math.floor(Math.random() * 10)}`,
      pod: `${service}-pod-${Math.floor(Math.random() * 100)}`,
      namespace: 'default'
    }
  };
}

/**
 * Main function
 */
async function main() {
  console.log('Logs Data Generator for Observability Agent UI');
  console.log('---------------------------------------------');
  console.log(`NATS URL: ${config.natsUrl}`);
  console.log(`Count: ${config.count}`);
  console.log(`Interval: ${config.interval}ms`);
  console.log(`Continuous: ${config.continuous}`);
  console.log(`Services: ${config.services.join(', ')}`);
  console.log('---------------------------------------------');
  
  try {
    // Connect to NATS
    const { nc, js } = await utils.connectToNATS(config.natsUrl);
    
    // Ensure LOGS stream exists
    await utils.ensureStream(js, 'LOGS', ['logs.*']);
    
    // Generate and publish logs
    let count = 0;
    
    async function publishLog() {
      if (!config.continuous && count >= config.count) {
        console.log(`Published ${count} logs. Done.`);
        await nc.drain();
        process.exit(0);
      }
      
      const log = generateLog();
      const subject = `logs.${log.service.replace(/-/g, '_')}.${log.level.toLowerCase()}`;
      
      const success = await utils.publishData(js, subject, log);
      
      if (success) {
        count++;
        console.log(`[${count}] Published log: [${log.level}] ${log.message} (${log.service})`);
      }
      
      if (config.continuous || count < config.count) {
        setTimeout(publishLog, config.interval);
      } else {
        console.log(`Published ${count} logs. Done.`);
        await nc.drain();
        process.exit(0);
      }
    }
    
    // Start publishing
    publishLog();
    
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
