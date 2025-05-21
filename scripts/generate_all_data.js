#!/usr/bin/env node
/**
 * All-in-One Data Generator for Observability Agent UI
 *
 * This script generates and publishes sample data for all components to NATS for the UI to consume.
 *
 * Usage:
 *   node generate_all_data.js [options]
 *
 * Options:
 *   --nats-url=<url>       NATS server URL (default: nats://localhost:4222)
 *   --duration=<seconds>   How long to run in seconds (default: 300)
 *   --continuous           Run continuously (default: false)
 *   --services=<list>      Comma-separated list of services (default: payment-service,order-service,inventory-service,api-gateway)
 *   --components=<list>    Comma-separated list of components to generate data for (default: all)
 *                          Available components: metrics,logs,deployments,agents,traces,rootcauses,notifications,postmortems,runbooks,runbook_executions,alerts
 *
 * Example:
 *   node generate_all_data.js --nats-url=nats://localhost:4222 --duration=600 --components=metrics,logs,alerts
 */

const { spawn } = require('child_process');
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
  duration: parseInt(args['duration'] || '300'),
  continuous: args['continuous'] === true,
  services: args['services'] || 'payment-service,order-service,inventory-service,api-gateway',
  components: (args['components'] || 'metrics,logs,deployments,agents,traces,rootcauses,notifications,postmortems,runbooks,runbook_executions,alerts').split(',')
};

// Component configurations
const componentConfigs = {
  metrics: {
    script: 'publish_metrics.js',
    interval: 5000,
    count: Math.ceil(config.duration / 5)
  },
  logs: {
    script: 'publish_logs.js',
    interval: 2000,
    count: Math.ceil(config.duration / 2)
  },
  deployments: {
    script: 'publish_deployments.js',
    interval: 30000,
    count: Math.ceil(config.duration / 30)
  },
  agents: {
    script: 'publish_agent_status.js',
    interval: 10000,
    duration: config.duration
  },
  traces: {
    script: 'publish_traces.js',
    interval: 8000,
    count: Math.ceil(config.duration / 8)
  },
  rootcauses: {
    script: 'publish_rootcauses.js',
    interval: 45000,
    count: Math.ceil(config.duration / 45)
  },
  notifications: {
    script: 'publish_notifications.js',
    interval: 15000,
    count: Math.ceil(config.duration / 15)
  },
  postmortems: {
    script: 'publish_postmortems.js',
    interval: 60000,
    count: Math.ceil(config.duration / 60)
  },
  runbooks: {
    script: 'publish_runbooks.js',
    interval: 20000,
    count: Math.ceil(config.duration / 20)
  },
  runbook_executions: {
    script: 'publish_runbook_executions.js',
    interval: 25000,
    count: Math.ceil(config.duration / 25)
  },
  alerts: {
    script: 'publish_alerts.js',
    interval: 10000,
    count: Math.ceil(config.duration / 10)
  }
};

/**
 * Run a data generator script as a child process
 * @param {string} component - Component name
 * @returns {Promise<Object>} - Child process
 */
function runGenerator(component) {
  return new Promise((resolve, reject) => {
    const config = componentConfigs[component];
    if (!config) {
      return reject(new Error(`Unknown component: ${component}`));
    }

    // Build command line arguments
    const args = [
      `--nats-url=${config.natsUrl}`,
      `--interval=${config.interval}`
    ];

    if (config.continuous) {
      args.push('--continuous');
    } else if (config.count) {
      args.push(`--count=${config.count}`);
    }

    if (config.duration) {
      args.push(`--duration=${config.duration}`);
    }

    if (config.services) {
      args.push(`--services=${config.services}`);
    }

    // Spawn the process
    console.log(`Starting ${component} generator: node scripts/${config.script} ${args.join(' ')}`);
    const child = spawn('node', [`scripts/${config.script}`, ...args], {
      stdio: 'pipe',
      shell: true
    });

    // Handle output
    child.stdout.on('data', (data) => {
      const lines = data.toString().trim().split('\n');
      lines.forEach(line => {
        if (line.trim()) {
          console.log(`[${component}] ${line}`);
        }
      });
    });

    child.stderr.on('data', (data) => {
      const lines = data.toString().trim().split('\n');
      lines.forEach(line => {
        if (line.trim()) {
          console.error(`[${component}] ERROR: ${line}`);
        }
      });
    });

    child.on('error', (error) => {
      console.error(`[${component}] Failed to start: ${error.message}`);
      reject(error);
    });

    child.on('close', (code) => {
      if (code === 0) {
        console.log(`[${component}] Generator completed successfully`);
        resolve(child);
      } else {
        console.error(`[${component}] Generator exited with code ${code}`);
        reject(new Error(`Process exited with code ${code}`));
      }
    });

    // Return the child process
    resolve(child);
  });
}

/**
 * Main function
 */
async function main() {
  console.log('All-in-One Data Generator for Observability Agent UI');
  console.log('--------------------------------------------------');
  console.log(`NATS URL: ${config.natsUrl}`);
  console.log(`Duration: ${config.duration}s`);
  console.log(`Continuous: ${config.continuous}`);
  console.log(`Services: ${config.services}`);
  console.log(`Components: ${config.components.join(', ')}`);
  console.log('--------------------------------------------------');

  try {
    // Verify NATS connection first
    const { nc } = await utils.connectToNATS(config.natsUrl);
    await nc.drain();
    console.log('NATS connection verified');

    // Update component configs with global settings
    Object.keys(componentConfigs).forEach(component => {
      componentConfigs[component].natsUrl = config.natsUrl;
      componentConfigs[component].continuous = config.continuous;
      componentConfigs[component].services = config.services;
    });

    // Start generators for selected components
    const processes = [];
    const validComponents = config.components.filter(c => componentConfigs[c]);

    if (validComponents.length === 0) {
      console.error('No valid components specified');
      process.exit(1);
    }

    console.log(`Starting generators for: ${validComponents.join(', ')}`);

    for (const component of validComponents) {
      try {
        const process = await runGenerator(component);
        processes.push({ name: component, process });
      } catch (error) {
        console.error(`Failed to start ${component} generator: ${error.message}`);
      }
    }

    if (processes.length === 0) {
      console.error('No generators were started successfully');
      process.exit(1);
    }

    console.log(`Started ${processes.length} generators`);

    // Set up cleanup handler
    let shuttingDown = false;

    async function cleanup() {
      if (shuttingDown) return;
      shuttingDown = true;

      console.log('Shutting down generators...');

      for (const { name, process } of processes) {
        if (process && !process.killed) {
          console.log(`Terminating ${name} generator...`);
          process.kill();
        }
      }

      console.log('All generators terminated');
      process.exit(0);
    }

    // Handle termination signals
    process.on('SIGINT', cleanup);
    process.on('SIGTERM', cleanup);

    // If not running continuously, set a timeout to stop after the specified duration
    if (!config.continuous) {
      console.log(`Will run for ${config.duration} seconds`);
      setTimeout(() => {
        console.log(`Reached duration limit of ${config.duration} seconds`);
        cleanup();
      }, config.duration * 1000);
    }

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
