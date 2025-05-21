#!/usr/bin/env node
/**
 * Agent Status Data Generator for Observability Agent UI
 * 
 * This script generates and publishes sample agent status data to NATS for the UI to consume.
 * 
 * Usage:
 *   node publish_agent_status.js [options]
 * 
 * Options:
 *   --nats-url=<url>       NATS server URL (default: nats://localhost:4222)
 *   --interval=<ms>        Interval between publications in ms (default: 5000)
 *   --duration=<seconds>   How long to run in seconds (default: 60)
 *   --continuous           Run continuously (default: false)
 * 
 * Example:
 *   node publish_agent_status.js --nats-url=nats://localhost:4222 --continuous
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
  interval: parseInt(args['interval'] || '5000'),
  duration: parseInt(args['duration'] || '60'),
  continuous: args['continuous'] === true
};

// List of agents
const agents = [
  { id: 'metric-agent', name: 'Metric Agent' },
  { id: 'log-agent', name: 'Log Agent' },
  { id: 'deployment-agent', name: 'Deployment Agent' },
  { id: 'tracing-agent', name: 'Tracing Agent' },
  { id: 'root-cause-agent', name: 'Root Cause Agent' },
  { id: 'notification-agent', name: 'Notification Agent' },
  { id: 'postmortem-agent', name: 'Postmortem Agent' },
  { id: 'runbook-agent', name: 'Runbook Agent' }
];

// Agent statuses with weights
const agentStatuses = [
  { status: 'active', weight: 85 },
  { status: 'degraded', weight: 10 },
  { status: 'inactive', weight: 5 }
];

/**
 * Select an agent status based on weights
 * @returns {string} - Agent status
 */
function selectAgentStatus() {
  const totalWeight = agentStatuses.reduce((sum, status) => sum + status.weight, 0);
  let random = Math.random() * totalWeight;
  
  for (const status of agentStatuses) {
    if (random < status.weight) {
      return status.status;
    }
    random -= status.weight;
  }
  
  return 'active'; // Default fallback
}

/**
 * Generate agent status data
 * @param {Object} agent - Agent information
 * @returns {Object} - Agent status data
 */
function generateAgentStatus(agent) {
  const status = selectAgentStatus();
  
  return {
    id: agent.id,
    name: agent.name,
    status,
    timestamp: new Date().toISOString(),
    version: `v${utils.randomNumber(1, 3)}.${utils.randomNumber(0, 10)}.${utils.randomNumber(0, 20)}`,
    uptime_seconds: utils.randomNumber(60, 86400), // 1 minute to 1 day
    memory_usage_mb: utils.randomNumber(50, 500),
    cpu_usage_percent: utils.randomNumber(1, 80),
    metadata: {
      host: `${agent.id}-${utils.randomNumber(1, 5)}`,
      pod: `${agent.id}-pod-${utils.randomNumber(1, 10)}`,
      namespace: 'default',
      node: `worker-node-${utils.randomNumber(1, 5)}`
    }
  };
}

/**
 * Main function
 */
async function main() {
  console.log('Agent Status Data Generator for Observability Agent UI');
  console.log('----------------------------------------------------');
  console.log(`NATS URL: ${config.natsUrl}`);
  console.log(`Interval: ${config.interval}ms`);
  console.log(`Duration: ${config.duration}s`);
  console.log(`Continuous: ${config.continuous}`);
  console.log(`Agents: ${agents.map(a => a.id).join(', ')}`);
  console.log('----------------------------------------------------');
  
  try {
    // Connect to NATS
    const { nc, js } = await utils.connectToNATS(config.natsUrl);
    
    // Ensure AGENTS stream exists
    await utils.ensureStream(js, 'AGENTS', ['agent.status.*']);
    
    // Start time
    const startTime = Date.now();
    const endTime = startTime + (config.duration * 1000);
    
    // Generate and publish agent status
    async function publishAgentStatus() {
      const currentTime = Date.now();
      
      if (!config.continuous && currentTime >= endTime) {
        console.log(`Ran for ${config.duration} seconds. Done.`);
        await nc.drain();
        process.exit(0);
      }
      
      // Publish status for each agent
      for (const agent of agents) {
        const status = generateAgentStatus(agent);
        const subject = `agent.status.${agent.id}`;
        
        const success = await utils.publishData(js, subject, status);
        
        if (success) {
          console.log(`Published status for ${agent.name}: ${status.status} (Memory: ${status.memory_usage_mb}MB, CPU: ${status.cpu_usage_percent}%)`);
        }
      }
      
      if (config.continuous || currentTime < endTime) {
        setTimeout(publishAgentStatus, config.interval);
      } else {
        console.log(`Ran for ${config.duration} seconds. Done.`);
        await nc.drain();
        process.exit(0);
      }
    }
    
    // Start publishing
    publishAgentStatus();
    
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
