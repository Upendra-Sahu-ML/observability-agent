#!/usr/bin/env node
/**
 * Direct Kubernetes NATS Publisher for Observability Agent UI
 * 
 * This script publishes sample data directly to the NATS server running in Kubernetes.
 * It uses kubectl port-forward to access the NATS server.
 * 
 * Usage:
 *   node publish_to_k8s_nats.js [options]
 * 
 * Options:
 *   --count=<number>       Number of items to generate (default: 10)
 *   --interval=<ms>        Interval between publications in ms (default: 1000)
 *   --continuous           Run continuously (default: false)
 */

const { spawn } = require('child_process');
const { connect, StringCodec } = require('nats');

// String codec for encoding/decoding NATS messages
const sc = StringCodec();

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
  count: parseInt(args['count'] || '10'),
  interval: parseInt(args['interval'] || '1000'),
  continuous: args['continuous'] === true,
  services: ['payment-service', 'order-service', 'inventory-service', 'api-gateway']
};

// Helper functions
function randomItem(array) {
  return array[Math.floor(Math.random() * array.length)];
}

function randomNumber(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randomRecentTimestamp() {
  const now = new Date();
  const minutesAgo = randomNumber(0, 60);
  now.setMinutes(now.getMinutes() - minutesAgo);
  return now.toISOString();
}

function generateId() {
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
}

// Data generators
function generateMetric() {
  const service = randomItem(config.services);
  const metricTypes = ['CPU Usage', 'Memory Usage', 'Disk I/O', 'Network I/O', 'Request Rate', 'Error Rate', 'Latency', 'Throughput'];
  const metricType = randomItem(metricTypes);
  
  let value, unit;
  switch (metricType) {
    case 'CPU Usage':
      value = randomNumber(1, 100);
      unit = '%';
      break;
    case 'Memory Usage':
      value = randomNumber(100, 8192);
      unit = 'MB';
      break;
    case 'Disk I/O':
      value = randomNumber(1, 500);
      unit = 'MB/s';
      break;
    case 'Network I/O':
      value = randomNumber(1, 200);
      unit = 'MB/s';
      break;
    case 'Request Rate':
      value = randomNumber(1, 500);
      unit = 'req/s';
      break;
    case 'Error Rate':
      value = randomNumber(0, 20);
      unit = '%';
      break;
    case 'Latency':
      value = randomNumber(10, 5000);
      unit = 'ms';
      break;
    case 'Throughput':
      value = randomNumber(1, 100);
      unit = 'MB/s';
      break;
  }
  
  return {
    id: generateId(),
    timestamp: randomRecentTimestamp(),
    service: service,
    type: metricType,
    value: value,
    unit: unit,
    threshold: randomNumber(Math.floor(value * 0.8), Math.ceil(value * 1.2)),
    status: randomItem(['normal', 'warning', 'critical'])
  };
}

function generateLog() {
  const service = randomItem(config.services);
  const logLevels = ['INFO', 'WARN', 'ERROR', 'DEBUG'];
  const level = randomItem(logLevels);
  
  let message;
  switch (service) {
    case 'payment-service':
      message = randomItem([
        'Payment processed successfully',
        'Payment gateway connection established',
        'Payment verification completed',
        'Payment failed: insufficient funds',
        'Payment timeout after 5000ms'
      ]);
      break;
    case 'order-service':
      message = randomItem([
        'Order created successfully',
        'Order service started successfully',
        'Order status updated',
        'High volume of orders detected',
        'Order processing delayed'
      ]);
      break;
    case 'inventory-service':
      message = randomItem([
        'Inventory updated for product',
        'Inventory check completed for order',
        'Low stock alert for product',
        'Inventory sync completed',
        'Inventory service health check passed'
      ]);
      break;
    case 'api-gateway':
      message = randomItem([
        'Request processed',
        'Rate limit exceeded for client',
        'Authentication failed for request',
        'Processed requests in the last minute',
        'API Gateway started successfully'
      ]);
      break;
  }
  
  // Add some randomness to the message
  if (message.includes('product')) {
    message = message.replace('product', `product #${randomNumber(1000, 9999)}`);
  }
  if (message.includes('order')) {
    message = message.replace('order', `order #${randomNumber(1000, 99999)}`);
  }
  
  return {
    id: generateId(),
    timestamp: randomRecentTimestamp(),
    service: service,
    level: level,
    message: message,
    trace_id: generateId()
  };
}

function generateAlert() {
  const service = randomItem(config.services);
  const alertTypes = {
    'payment-service': [
      { name: 'PaymentGatewayTimeout', description: 'Payment gateway timeout: ${value}ms (threshold: ${threshold}ms)', value: randomNumber(5000, 15000), threshold: 5000 },
      { name: 'HighPaymentFailureRate', description: 'High payment failure rate: ${value}% (threshold: ${threshold}%)', value: randomNumber(10, 30), threshold: 10 },
      { name: 'DatabaseConnectionPoolExhaustion', description: 'Database connection pool exhaustion: ${value}% (threshold: ${threshold}%)', value: randomNumber(85, 100), threshold: 90 },
      { name: 'HighCpuUsage', description: 'High CPU usage detected: ${value}% (threshold: ${threshold}%)', value: randomNumber(80, 100), threshold: 80 }
    ],
    'order-service': [
      { name: 'OrderProcessingDelay', description: 'Order processing delay: ${value}s (threshold: ${threshold}s)', value: randomNumber(10, 60), threshold: 10 },
      { name: 'DatabaseQueryTimeout', description: 'Database query timeout: ${value} timeouts/minute (threshold: ${threshold} timeouts/minute)', value: randomNumber(5, 20), threshold: 5 },
      { name: 'HighMemoryUsage', description: 'High memory usage: ${value}% (threshold: ${threshold}%)', value: randomNumber(85, 100), threshold: 85 }
    ],
    'inventory-service': [
      { name: 'LowStockAlert', description: 'Low stock alert: ${value} items remaining (threshold: ${threshold} items)', value: randomNumber(1, 10), threshold: 10 },
      { name: 'InventorySyncFailure', description: 'Inventory sync failure: ${value} consecutive failures (threshold: ${threshold} failures)', value: randomNumber(3, 10), threshold: 3 },
      { name: 'SlowDatabaseQueries', description: 'Slow database queries: ${value}ms average (threshold: ${threshold}ms)', value: randomNumber(500, 2000), threshold: 500 }
    ],
    'api-gateway': [
      { name: 'HighRequestLatency', description: 'High request latency: ${value}ms (threshold: ${threshold}ms)', value: randomNumber(1000, 5000), threshold: 1000 },
      { name: 'IncreasedErrorResponses', description: 'Increased error responses: ${value}% (threshold: ${threshold}%)', value: randomNumber(5, 20), threshold: 5 },
      { name: 'RateLimitExceeded', description: 'Rate limit exceeded: ${value} req/s (threshold: ${threshold} req/s)', value: randomNumber(100, 500), threshold: 100 }
    ]
  };
  
  const alertType = randomItem(alertTypes[service]);
  const status = randomItem(['open', 'acknowledged', 'resolved']);
  const created = randomRecentTimestamp();
  
  // Format the description with actual values
  const description = alertType.description
    .replace('${value}', alertType.value)
    .replace('${threshold}', alertType.threshold);
  
  return {
    id: generateId(),
    name: alertType.name,
    service: service,
    description: description,
    status: status,
    severity: randomItem(['critical', 'warning', 'info']),
    created_at: created,
    updated_at: status === 'open' ? created : randomRecentTimestamp(),
    resolved_at: status === 'resolved' ? randomRecentTimestamp() : null
  };
}

// Main function
async function main() {
  console.log(`Direct Kubernetes NATS Publisher for Observability Agent UI`);
  console.log(`----------------------------------------------`);
  console.log(`Count: ${config.count}`);
  console.log(`Interval: ${config.interval}ms`);
  console.log(`Continuous: ${config.continuous}`);
  console.log(`Services: ${config.services.join(', ')}`);
  console.log(`----------------------------------------------`);
  
  // Start port-forwarding to NATS
  console.log('Starting port-forward to NATS in Kubernetes...');
  const portForward = spawn('kubectl', ['port-forward', '-n', 'observability', 'svc/observability-agent-nats', '4222:4222']);
  
  // Wait for port-forward to be ready
  await new Promise(resolve => setTimeout(resolve, 2000));
  
  try {
    // Connect to NATS
    console.log('Connecting to NATS server at nats://localhost:4222...');
    const nc = await connect({
      servers: 'nats://localhost:4222',
      timeout: 5000
    });
    
    console.log('Connected to NATS server');
    
    // Publish data
    let count = 0;
    
    const publishData = async () => {
      // Publish a metric
      const metric = generateMetric();
      const metricSubject = `metrics.${metric.service}`;
      await nc.publish(metricSubject, sc.encode(JSON.stringify(metric)));
      console.log(`[${count+1}] Published metric: ${metric.type} = ${metric.value}${metric.unit} for ${metric.service}`);
      
      // Publish a log
      const log = generateLog();
      const logSubject = `logs.${log.service}`;
      await nc.publish(logSubject, sc.encode(JSON.stringify(log)));
      console.log(`[${count+1}] Published log: [${log.level}] ${log.message} (${log.service})`);
      
      // Publish an alert
      const alert = generateAlert();
      const alertSubject = `alerts.${alert.service}`;
      await nc.publish(alertSubject, sc.encode(JSON.stringify(alert)));
      console.log(`[${count+1}] Published alert: ${alert.name} (${alert.service}, ${alert.status})`);
      
      count++;
      
      if (count >= config.count && !config.continuous) {
        console.log(`Published ${count} items of each type. Done.`);
        await nc.drain();
        portForward.kill();
        process.exit(0);
      }
    };
    
    // Initial publish
    await publishData();
    
    // Set up interval for continuous publishing
    if (config.continuous || count < config.count) {
      const interval = setInterval(async () => {
        await publishData();
        if (count >= config.count && !config.continuous) {
          clearInterval(interval);
          console.log(`Published ${count} items of each type. Done.`);
          await nc.drain();
          portForward.kill();
          process.exit(0);
        }
      }, config.interval);
      
      // Handle Ctrl+C
      process.on('SIGINT', async () => {
        clearInterval(interval);
        console.log('\nInterrupted. Disconnecting from NATS...');
        await nc.drain();
        portForward.kill();
        process.exit(0);
      });
    }
  } catch (error) {
    console.error(`Error: ${error.message}`);
    portForward.kill();
    process.exit(1);
  }
}

// Run the main function
main().catch(err => {
  console.error(`Fatal error: ${err.message}`);
  process.exit(1);
});
