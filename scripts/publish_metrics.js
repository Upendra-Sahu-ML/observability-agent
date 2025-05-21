#!/usr/bin/env node
/**
 * Metrics Data Generator for Observability Agent UI
 * 
 * This script generates and publishes sample metrics data to NATS for the UI to consume.
 * 
 * Usage:
 *   node publish_metrics.js [options]
 * 
 * Options:
 *   --nats-url=<url>       NATS server URL (default: nats://localhost:4222)
 *   --count=<number>       Number of metrics to generate (default: 20)
 *   --interval=<ms>        Interval between publications in ms (default: 1000)
 *   --continuous           Run continuously (default: false)
 *   --services=<list>      Comma-separated list of services (default: payment-service,order-service,inventory-service,api-gateway)
 * 
 * Example:
 *   node publish_metrics.js --nats-url=nats://localhost:4222 --count=50 --continuous
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
  count: parseInt(args['count'] || '20'),
  interval: parseInt(args['interval'] || '1000'),
  continuous: args['continuous'] === true,
  services: (args['services'] || 'payment-service,order-service,inventory-service,api-gateway').split(',')
};

// Metric types to generate
const metricTypes = [
  { name: 'CPU Usage', unit: '%', min: 0, max: 100, format: (val) => `${val}%` },
  { name: 'Memory Usage', unit: 'MB', min: 100, max: 8192, format: (val) => `${val}MB` },
  { name: 'Request Rate', unit: 'req/s', min: 10, max: 500, format: (val) => `${val} req/s` },
  { name: 'Error Rate', unit: '%', min: 0, max: 10, format: (val) => `${val}%` },
  { name: 'Latency', unit: 'ms', min: 10, max: 5000, format: (val) => `${val}ms` },
  { name: 'Throughput', unit: 'MB/s', min: 1, max: 100, format: (val) => `${val}MB/s` },
  { name: 'Disk Usage', unit: '%', min: 10, max: 95, format: (val) => `${val}%` },
  { name: 'Network I/O', unit: 'MB/s', min: 1, max: 200, format: (val) => `${val}MB/s` }
];

/**
 * Generate a random metric
 * @returns {Object} - Random metric data
 */
function generateMetric() {
  const service = utils.randomItem(config.services);
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
}

/**
 * Main function
 */
async function main() {
  console.log('Metrics Data Generator for Observability Agent UI');
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
    
    // Ensure METRICS stream exists
    await utils.ensureStream(js, 'METRICS', ['metrics.*']);
    
    // Generate and publish metrics
    let count = 0;
    
    async function publishMetrics() {
      if (!config.continuous && count >= config.count) {
        console.log(`Published ${count} metrics. Done.`);
        await nc.drain();
        process.exit(0);
      }
      
      const metric = generateMetric();
      const subject = `metrics.${metric.service.replace(/-/g, '_')}.${metric.name.toLowerCase().replace(/\s+/g, '_')}`;
      
      const success = await utils.publishData(js, subject, metric);
      
      if (success) {
        count++;
        console.log(`[${count}] Published metric: ${metric.name} = ${metric.value} for ${metric.service}`);
      }
      
      if (config.continuous || count < config.count) {
        setTimeout(publishMetrics, config.interval);
      } else {
        console.log(`Published ${count} metrics. Done.`);
        await nc.drain();
        process.exit(0);
      }
    }
    
    // Start publishing
    publishMetrics();
    
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
