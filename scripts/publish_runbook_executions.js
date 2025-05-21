#!/usr/bin/env node
/**
 * Runbook Execution Data Generator for Observability Agent UI
 * 
 * This script generates and publishes sample runbook execution data to NATS for the UI to consume.
 * 
 * Usage:
 *   node publish_runbook_executions.js [options]
 * 
 * Options:
 *   --nats-url=<url>       NATS server URL (default: nats://localhost:4222)
 *   --count=<number>       Number of executions to generate (default: 5)
 *   --interval=<ms>        Interval between publications in ms (default: 3000)
 *   --continuous           Run continuously (default: false)
 *   --services=<list>      Comma-separated list of services (default: payment-service,order-service,inventory-service,api-gateway)
 * 
 * Example:
 *   node publish_runbook_executions.js --nats-url=nats://localhost:4222 --count=3
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

// Runbook execution templates
const executionTemplates = [
  {
    title: 'Database Connection Issues',
    steps: [
      {
        name: 'Check database connection pool settings',
        outputs: [
          'Current pool size: 20',
          'Max pool size: 50',
          'Active connections: 18',
          'Connection timeout: 30s'
        ]
      },
      {
        name: 'Verify database server is running',
        outputs: [
          'Database server status: running',
          'Uptime: 15 days, 7 hours',
          'Current connections: 42'
        ]
      },
      {
        name: 'Check for network connectivity issues',
        outputs: [
          'Network latency to database: 2ms',
          'No packet loss detected',
          'Network utilization: 35%'
        ]
      },
      {
        name: 'Restart the service if necessary',
        outputs: [
          'Service restart not required',
          'All connectivity checks passed'
        ]
      }
    ]
  },
  {
    title: 'High CPU Usage Remediation',
    steps: [
      {
        name: 'Identify processes consuming high CPU',
        outputs: [
          'Top CPU consumers:',
          '1. java (pid 1234): 85%',
          '2. node (pid 5678): 45%',
          '3. python (pid 9012): 30%'
        ]
      },
      {
        name: 'Check for recent code deployments',
        outputs: [
          'Recent deployments:',
          '- v2.3.1 deployed 2 hours ago',
          '- v2.3.0 deployed 2 days ago'
        ]
      },
      {
        name: 'Look for unusual traffic patterns',
        outputs: [
          'Traffic increased by 40% in the last hour',
          'Request rate: 250 req/s (normal: 150 req/s)',
          'Possible DDoS attack detected'
        ]
      },
      {
        name: 'Scale up the service horizontally',
        outputs: [
          'Scaling up from 3 to 5 instances',
          'New instances launching...',
          'Instances ready and serving traffic'
        ]
      }
    ]
  },
  {
    title: 'Memory Leak Remediation',
    steps: [
      {
        name: 'Take heap dump of the affected service',
        outputs: [
          'Heap dump saved to /tmp/heapdump-20230615-123456.hprof',
          'Heap dump size: 256MB'
        ]
      },
      {
        name: 'Analyze memory usage patterns',
        outputs: [
          'Memory analysis results:',
          '- 75% of heap used by HashMap objects',
          '- Suspicious growth pattern in RequestCache class',
          '- Possible memory leak in connection handling'
        ]
      },
      {
        name: 'Identify objects with unusual retention',
        outputs: [
          'Found 15,000 instances of RequestContext not being released',
          'Objects retained by static reference in RequestProcessor',
          'Issue identified in RequestProcessor.processAsync method'
        ]
      },
      {
        name: 'Apply fix to release references properly',
        outputs: [
          'Deployed hotfix v2.3.2',
          'Fixed reference handling in RequestProcessor',
          'Memory usage stabilized'
        ]
      }
    ]
  }
];

// Execution statuses
const executionStatuses = ['running', 'completed', 'failed', 'paused'];

/**
 * Generate a random runbook execution
 * @returns {Object} - Runbook execution data
 */
function generateExecution() {
  const service = utils.randomItem(config.services);
  const template = utils.randomItem(executionTemplates);
  const status = utils.randomItem(executionStatuses);
  
  // For completed or failed executions, include all steps
  // For running or paused, include only some steps
  const completedStepCount = (status === 'completed' || status === 'failed') 
    ? template.steps.length 
    : utils.randomNumber(1, template.steps.length - 1);
  
  // Generate steps with status and output
  const steps = template.steps.map((step, index) => {
    let stepStatus;
    
    if (index < completedStepCount) {
      // Step is completed
      stepStatus = status === 'failed' && index === completedStepCount - 1 ? 'failed' : 'completed';
    } else if (index === completedStepCount) {
      // Current step
      stepStatus = status === 'running' ? 'running' : 'pending';
    } else {
      // Future step
      stepStatus = 'pending';
    }
    
    return {
      name: step.name,
      status: stepStatus,
      output: stepStatus === 'pending' ? [] : step.outputs.slice(0, stepStatus === 'running' ? utils.randomNumber(1, step.outputs.length) : step.outputs.length),
      startTime: stepStatus !== 'pending' ? new Date(Date.now() - utils.randomNumber(5, 30) * 60 * 1000).toISOString() : null,
      endTime: stepStatus === 'completed' || stepStatus === 'failed' ? new Date(Date.now() - utils.randomNumber(1, 5) * 60 * 1000).toISOString() : null
    };
  });
  
  return {
    id: utils.generateId('exec'),
    runbookId: utils.generateId('rb'),
    alertId: utils.generateId('alert'),
    title: template.title,
    service,
    status,
    steps,
    startTime: new Date(Date.now() - utils.randomNumber(10, 60) * 60 * 1000).toISOString(),
    endTime: (status === 'completed' || status === 'failed') ? new Date(Date.now() - utils.randomNumber(1, 10) * 60 * 1000).toISOString() : null,
    executedBy: utils.randomItem(['system', 'admin', 'sre-team', 'devops']),
    summary: status === 'completed' ? 'Execution completed successfully' : 
             status === 'failed' ? `Execution failed at step ${completedStepCount}` :
             status === 'paused' ? 'Execution paused by user' :
             'Execution in progress'
  };
}

/**
 * Main function
 */
async function main() {
  console.log('Runbook Execution Data Generator for Observability Agent UI');
  console.log('--------------------------------------------------------');
  console.log(`NATS URL: ${config.natsUrl}`);
  console.log(`Count: ${config.count}`);
  console.log(`Interval: ${config.interval}ms`);
  console.log(`Continuous: ${config.continuous}`);
  console.log(`Services: ${config.services.join(', ')}`);
  console.log('--------------------------------------------------------');
  
  try {
    // Connect to NATS
    const { nc, js } = await utils.connectToNATS(config.natsUrl);
    
    // Ensure RUNBOOK_EXECUTIONS stream exists
    await utils.ensureStream(js, 'RUNBOOK_EXECUTIONS', ['runbook.execute', 'runbook.status.*']);
    
    // Generate and publish runbook executions
    let count = 0;
    
    async function publishExecution() {
      if (!config.continuous && count >= config.count) {
        console.log(`Published ${count} runbook executions. Done.`);
        await nc.drain();
        process.exit(0);
      }
      
      const execution = generateExecution();
      
      // Use the correct subject pattern for RUNBOOK_EXECUTIONS
      const subject = `runbook.status.${execution.service.replace(/-/g, '_')}`;
      
      const success = await utils.publishData(js, subject, execution);
      
      if (success) {
        count++;
        console.log(`[${count}] Published execution: ${execution.title} (${execution.service}, ${execution.status})`);
        console.log(`    Steps: ${execution.steps.filter(s => s.status === 'completed').length}/${execution.steps.length} completed`);
      }
      
      if (config.continuous || count < config.count) {
        setTimeout(publishExecution, config.interval);
      } else {
        console.log(`Published ${count} runbook executions. Done.`);
        await nc.drain();
        process.exit(0);
      }
    }
    
    // Start publishing
    publishExecution();
    
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
