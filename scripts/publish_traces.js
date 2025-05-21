#!/usr/bin/env node
/**
 * Tracing Data Generator for Observability Agent UI
 *
 * This script generates and publishes sample tracing data to NATS for the UI to consume.
 *
 * Usage:
 *   node publish_traces.js [options]
 *
 * Options:
 *   --nats-url=<url>       NATS server URL (default: nats://localhost:4222)
 *   --count=<number>       Number of traces to generate (default: 15)
 *   --interval=<ms>        Interval between publications in ms (default: 2000)
 *   --continuous           Run continuously (default: false)
 *   --services=<list>      Comma-separated list of services (default: api-gateway,payment-service,order-service,inventory-service,user-service)
 *
 * Example:
 *   node publish_traces.js --nats-url=nats://localhost:4222 --count=10 --continuous
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
  services: (args['services'] || 'api-gateway,payment-service,order-service,inventory-service,user-service').split(',')
};

// Common operations by service
const serviceOperations = {
  'api-gateway': [
    'GET /api/orders',
    'POST /api/orders',
    'GET /api/products',
    'GET /api/users',
    'POST /api/payments',
    'handleRequest',
    'validateRequest',
    'routeRequest',
    'applyRateLimiting',
    'authenticateUser'
  ],
  'payment-service': [
    'processPayment',
    'validatePaymentDetails',
    'connectToPaymentGateway',
    'recordTransaction',
    'sendPaymentConfirmation',
    'checkFraud',
    'applyDiscount',
    'calculateTax',
    'refundPayment',
    'getPaymentStatus'
  ],
  'order-service': [
    'createOrder',
    'updateOrderStatus',
    'getOrderDetails',
    'cancelOrder',
    'validateOrderItems',
    'calculateOrderTotal',
    'applyPromoCode',
    'checkInventory',
    'notifyShipping',
    'getOrderHistory'
  ],
  'inventory-service': [
    'checkStock',
    'updateInventory',
    'reserveItems',
    'releaseReservation',
    'getProductDetails',
    'notifyLowStock',
    'syncInventory',
    'getInventoryReport',
    'addNewProduct',
    'removeProduct'
  ],
  'user-service': [
    'getUserProfile',
    'updateUserProfile',
    'authenticateUser',
    'registerUser',
    'resetPassword',
    'verifyEmail',
    'getUserPreferences',
    'updateUserPreferences',
    'deleteUser',
    'getUserActivity'
  ]
};

// HTTP methods for API operations
const httpMethods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'];

// Error types for failed spans
const errorTypes = [
  'timeout',
  'connection_error',
  'validation_error',
  'authentication_error',
  'authorization_error',
  'resource_not_found',
  'internal_server_error',
  'bad_request',
  'service_unavailable'
];

/**
 * Generate a random span
 * @param {string} traceId - Parent trace ID
 * @param {string} parentId - Parent span ID (optional)
 * @param {string} service - Service name
 * @param {number} depth - Current depth in the trace tree
 * @param {number} startTime - Start time in milliseconds
 * @returns {Object} - Span data
 */
function generateSpan(traceId, parentId, service, depth, startTime) {
  const id = utils.generateId('span');
  const operation = utils.randomItem(serviceOperations[service] || ['unknown']);

  // Determine if this is an HTTP operation
  const isHttpOperation = operation.includes('/');

  // Generate span data
  const duration = utils.randomNumber(5, 500); // 5ms to 500ms
  const endTime = startTime + duration;

  const span = {
    id,
    traceId,
    parentId,
    service,
    operation,
    startTime: new Date(startTime).toISOString(),
    endTime: new Date(endTime).toISOString(),
    duration,
    tags: {
      component: service,
      'span.kind': isHttpOperation ? 'server' : 'internal'
    }
  };

  // Add HTTP-specific tags for HTTP operations
  if (isHttpOperation) {
    const [method, path] = operation.split(' ');
    span.tags['http.method'] = method;
    span.tags['http.url'] = path;
    span.tags['http.status_code'] = utils.randomNumber(200, 500);
  }

  // Randomly add an error (5% chance)
  if (Math.random() < 0.05) {
    span.tags['error'] = true;
    span.tags['error.type'] = utils.randomItem(errorTypes);
    span.tags['error.message'] = `Error during ${operation}: ${span.tags['error.type']}`;
  }

  return {
    span,
    endTime
  };
}

/**
 * Generate a trace with multiple spans
 * @returns {Object} - Trace data with spans
 */
function generateTrace() {
  const traceId = utils.generateId('trace');
  const rootService = 'api-gateway'; // Always start with API gateway
  const rootOperation = utils.randomItem(serviceOperations[rootService].filter(op => op.includes('/')));

  // Start time between 5 minutes ago and now
  const now = Date.now();
  const fiveMinutesAgo = now - (5 * 60 * 1000);
  const startTime = utils.randomNumber(fiveMinutesAgo, now);

  // Generate root span
  const rootSpan = generateSpan(traceId, null, rootService, 0, startTime);
  const spans = [rootSpan.span];

  // Determine number of child spans (3-10)
  const childSpanCount = utils.randomNumber(3, 10);

  // Generate child spans
  let currentSpans = [rootSpan];

  // Generate up to 3 levels of spans
  for (let depth = 1; depth <= 3; depth++) {
    const nextLevelSpans = [];

    for (const parentSpan of currentSpans) {
      // 70% chance to generate child spans if we're not at max depth
      if (depth < 3 && Math.random() < 0.7) {
        // Generate 1-3 child spans
        const numChildren = utils.randomNumber(1, 3);

        for (let i = 0; i < numChildren; i++) {
          // Select a service for this span
          // If parent is API gateway, select a downstream service
          // Otherwise, 80% chance to stay in the same service
          let service;
          if (parentSpan.span.service === 'api-gateway') {
            service = utils.randomItem(config.services.filter(s => s !== 'api-gateway'));
          } else if (Math.random() < 0.8) {
            service = parentSpan.span.service;
          } else {
            service = utils.randomItem(config.services);
          }

          // Generate the span
          // Parse the parent start time to get a timestamp we can add to
          const parentStartTime = new Date(parentSpan.span.startTime).getTime();
          const childSpan = generateSpan(
            traceId,
            parentSpan.span.id,
            service,
            depth,
            parentStartTime + utils.randomNumber(1, 10)
          );

          spans.push(childSpan.span);
          nextLevelSpans.push(childSpan);
        }
      }
    }

    currentSpans = nextLevelSpans;

    // If no more spans at this level, break
    if (currentSpans.length === 0) {
      break;
    }
  }

  // Calculate total duration based on the latest span end time
  const latestEndTime = Math.max(...spans.map(span => new Date(span.endTime).getTime()));
  const totalDuration = latestEndTime - startTime;

  // Create the trace object
  return {
    id: traceId,
    service: rootService,
    operation: rootOperation,
    duration: totalDuration,
    timestamp: new Date(startTime).toISOString(),
    spans
  };
}

/**
 * Main function
 */
async function main() {
  console.log('Tracing Data Generator for Observability Agent UI');
  console.log('------------------------------------------------');
  console.log(`NATS URL: ${config.natsUrl}`);
  console.log(`Count: ${config.count}`);
  console.log(`Interval: ${config.interval}ms`);
  console.log(`Continuous: ${config.continuous}`);
  console.log(`Services: ${config.services.join(', ')}`);
  console.log('------------------------------------------------');

  try {
    // Connect to NATS
    const { nc, js } = await utils.connectToNATS(config.natsUrl);

    // Ensure TRACES stream exists
    await utils.ensureStream(js, 'TRACES', ['traces.*']);

    // Generate and publish traces
    let count = 0;

    async function publishTrace() {
      if (!config.continuous && count >= config.count) {
        console.log(`Published ${count} traces. Done.`);
        await nc.drain();
        process.exit(0);
      }

      const trace = generateTrace();
      const subject = `traces.${trace.service.replace(/-/g, '_')}`;

      const success = await utils.publishData(js, subject, trace);

      if (success) {
        count++;
        console.log(`[${count}] Published trace: ${trace.operation} with ${trace.spans.length} spans (${trace.duration}ms)`);
      }

      if (config.continuous || count < config.count) {
        setTimeout(publishTrace, config.interval);
      } else {
        console.log(`Published ${count} traces. Done.`);
        await nc.drain();
        process.exit(0);
      }
    }

    // Start publishing
    publishTrace();

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
