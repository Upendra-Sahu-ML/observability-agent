#!/usr/bin/env node
/**
 * Deployment Data Generator for Observability Agent UI
 * 
 * This script generates and publishes sample deployment data to NATS for the UI to consume.
 * 
 * Usage:
 *   node publish_deployments.js [options]
 * 
 * Options:
 *   --nats-url=<url>       NATS server URL (default: nats://localhost:4222)
 *   --count=<number>       Number of deployments to generate (default: 10)
 *   --interval=<ms>        Interval between publications in ms (default: 2000)
 *   --continuous           Run continuously (default: false)
 *   --services=<list>      Comma-separated list of services (default: payment-service,order-service,inventory-service,api-gateway)
 * 
 * Example:
 *   node publish_deployments.js --nats-url=nats://localhost:4222 --count=5
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
  count: parseInt(args['count'] || '10'),
  interval: parseInt(args['interval'] || '2000'),
  continuous: args['continuous'] === true,
  services: (args['services'] || 'payment-service,order-service,inventory-service,api-gateway').split(',')
};

// Deployment statuses with weights
const deploymentStatuses = [
  { status: 'deployed', weight: 70 },
  { status: 'failed', weight: 15 },
  { status: 'in_progress', weight: 10 },
  { status: 'cancelled', weight: 5 }
];

// Failure reasons for failed deployments
const failureReasons = [
  'Container image pull failure',
  'Resource limits exceeded',
  'Configuration error',
  'Liveness probe failed',
  'Readiness probe failed',
  'Init container failed',
  'Pod evicted',
  'Node failure',
  'Network connectivity issues',
  'Permission denied'
];

/**
 * Select a deployment status based on weights
 * @returns {string} - Deployment status
 */
function selectDeploymentStatus() {
  const totalWeight = deploymentStatuses.reduce((sum, status) => sum + status.weight, 0);
  let random = Math.random() * totalWeight;
  
  for (const status of deploymentStatuses) {
    if (random < status.weight) {
      return status.status;
    }
    random -= status.weight;
  }
  
  return 'deployed'; // Default fallback
}

/**
 * Generate a semantic version
 * @returns {string} - Semantic version
 */
function generateVersion() {
  const major = utils.randomNumber(1, 5);
  const minor = utils.randomNumber(0, 15);
  const patch = utils.randomNumber(0, 20);
  return `v${major}.${minor}.${patch}`;
}

/**
 * Generate a random deployment
 * @returns {Object} - Deployment data
 */
function generateDeployment() {
  const service = utils.randomItem(config.services);
  const status = selectDeploymentStatus();
  const version = generateVersion();
  const timestamp = new Date().toISOString();
  
  const deployment = {
    id: utils.generateId('deploy'),
    service,
    version,
    status,
    timestamp,
    user: utils.randomItem(['system', 'admin', 'ci-pipeline', 'jenkins', 'github-actions']),
    environment: utils.randomItem(['production', 'staging', 'development', 'testing']),
    namespace: utils.randomItem(['default', 'prod', 'staging', 'dev']),
    metadata: {
      commit_hash: Math.random().toString(16).substring(2, 10),
      build_number: utils.randomNumber(100, 9999),
      build_url: `https://ci.example.com/builds/${utils.randomNumber(1000, 9999)}`,
      duration_seconds: utils.randomNumber(30, 600)
    }
  };
  
  // Add failure reason for failed deployments
  if (status === 'failed') {
    deployment.failure_reason = utils.randomItem(failureReasons);
  }
  
  return deployment;
}

/**
 * Main function
 */
async function main() {
  console.log('Deployment Data Generator for Observability Agent UI');
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
    
    // Ensure DEPLOYMENTS stream exists
    await utils.ensureStream(js, 'DEPLOYMENTS', ['deployments.*']);
    
    // Generate and publish deployments
    let count = 0;
    
    async function publishDeployment() {
      if (!config.continuous && count >= config.count) {
        console.log(`Published ${count} deployments. Done.`);
        await nc.drain();
        process.exit(0);
      }
      
      const deployment = generateDeployment();
      const subject = `deployments.${deployment.service.replace(/-/g, '_')}`;
      
      const success = await utils.publishData(js, subject, deployment);
      
      if (success) {
        count++;
        console.log(`[${count}] Published deployment: ${deployment.service} ${deployment.version} (${deployment.status})`);
        if (deployment.failure_reason) {
          console.log(`    Failure reason: ${deployment.failure_reason}`);
        }
      }
      
      if (config.continuous || count < config.count) {
        setTimeout(publishDeployment, config.interval);
      } else {
        console.log(`Published ${count} deployments. Done.`);
        await nc.drain();
        process.exit(0);
      }
    }
    
    // Start publishing
    publishDeployment();
    
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
