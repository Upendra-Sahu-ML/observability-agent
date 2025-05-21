#!/usr/bin/env node
/**
 * Test Data Publisher for Observability Agent
 * 
 * This script publishes test data to all required NATS streams with the correct subjects.
 * 
 * Usage:
 *   node publish_test_data.js [--nats-url=<url>] [--stream=<stream>]
 * 
 * Options:
 *   --nats-url=<url>   NATS server URL (default: nats://localhost:4222)
 *   --stream=<stream>  Only publish to specific stream (default: all streams)
 */

const { connect, StringCodec } = require('nats');

// Parse command line arguments
const args = process.argv.slice(2).reduce((acc, arg) => {
  if (arg.startsWith('--')) {
    const [key, value] = arg.substring(2).split('=');
    acc[key] = value !== undefined ? value : true;
  }
  return acc;
}, {});

// Configuration
const config = {
  natsUrl: args['nats-url'] || 'nats://localhost:4222',
  specificStream: args['stream'] || null
};

// String codec for encoding/decoding NATS messages
const sc = StringCodec();

// Helper functions
function generateId(prefix = '') {
  return `${prefix}${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

function randomNumber(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randomItem(array) {
  return array[Math.floor(Math.random() * array.length)];
}

// Stream definitions with sample data generators
const streamDefinitions = [
  {
    name: 'ALERTS',
    subjects: ['alerts', 'alerts.test'],
    dataGenerator: () => ({
      id: generateId('alert-'),
      labels: {
        alertname: 'HighCpuUsage',
        service: 'payment-service',
        severity: 'warning',
        instance: `payment-service-${randomNumber(1, 5)}`,
        namespace: 'default'
      },
      annotations: {
        summary: 'High CPU usage detected',
        description: 'CPU usage above threshold for payment-service',
        value: `${randomNumber(80, 95)}%`,
        threshold: '80%'
      },
      startsAt: new Date(Date.now() - randomNumber(5, 60) * 60 * 1000).toISOString(),
      endsAt: null,
      status: 'open'
    })
  },
  {
    name: 'METRICS',
    subjects: ['metrics', 'metrics.test'],
    dataGenerator: () => ({
      id: generateId('metric-'),
      timestamp: new Date().toISOString(),
      service: 'payment-service',
      instance: `payment-service-${randomNumber(1, 5)}`,
      metrics: {
        cpu_usage: randomNumber(0, 100),
        memory_usage: randomNumber(0, 100),
        request_count: randomNumber(100, 5000),
        error_rate: randomNumber(0, 10),
        latency_p95: randomNumber(50, 500)
      }
    })
  },
  {
    name: 'LOGS',
    subjects: ['logs', 'logs.test'],
    dataGenerator: () => ({
      id: generateId('log-'),
      timestamp: new Date().toISOString(),
      service: 'payment-service',
      instance: `payment-service-${randomNumber(1, 5)}`,
      level: randomItem(['INFO', 'WARN', 'ERROR']),
      message: `Sample log message ${randomNumber(1, 1000)}`,
      context: {
        requestId: generateId('req-'),
        userId: generateId('user-'),
        path: '/api/payments'
      }
    })
  },
  {
    name: 'DEPLOYMENTS',
    subjects: ['deployments', 'deployments.test'],
    dataGenerator: () => ({
      id: generateId('deploy-'),
      timestamp: new Date().toISOString(),
      service: 'payment-service',
      version: `v1.${randomNumber(0, 9)}.${randomNumber(0, 99)}`,
      status: randomItem(['success', 'in_progress', 'failed']),
      changes: {
        added: randomNumber(0, 10),
        modified: randomNumber(0, 20),
        removed: randomNumber(0, 5)
      }
    })
  },
  {
    name: 'TRACES',
    subjects: ['traces', 'traces.test'],
    dataGenerator: () => ({
      id: generateId('trace-'),
      traceId: generateId('trace-'),
      timestamp: new Date().toISOString(),
      service: 'payment-service',
      name: 'process-payment',
      duration: randomNumber(10, 1000),
      status: randomItem(['success', 'error']),
      spans: [
        {
          id: generateId('span-'),
          name: 'validate-payment',
          duration: randomNumber(5, 100)
        },
        {
          id: generateId('span-'),
          name: 'process-transaction',
          duration: randomNumber(5, 500)
        }
      ]
    })
  },
  {
    name: 'ROOT_CAUSE',
    subjects: ['root_cause_analysis', 'rootcause.test'],
    dataGenerator: () => ({
      id: generateId('rootcause-'),
      alertId: generateId('alert-'),
      timestamp: new Date().toISOString(),
      service: 'payment-service',
      analysis: {
        cause: 'Database connection pool exhaustion',
        confidence: randomNumber(70, 100),
        evidence: [
          'High database connection count',
          'Increased latency in database queries',
          'Connection timeout errors in logs'
        ],
        recommendation: 'Increase connection pool size or implement connection pooling'
      }
    })
  },
  {
    name: 'RUNBOOKS',
    subjects: ['runbooks', 'runbook.data.test'],
    dataGenerator: () => ({
      id: generateId('runbook-'),
      name: 'Fix Database Connection Issues',
      description: 'Steps to resolve database connection pool exhaustion',
      service: 'payment-service',
      steps: [
        'Check current connection pool settings',
        'Verify active connections count',
        'Increase max_connections parameter',
        'Restart database service if needed',
        'Monitor connection count after changes'
      ],
      tags: ['database', 'connection-pool', 'performance']
    })
  },
  {
    name: 'RUNBOOK_EXECUTIONS',
    subjects: ['runbook.execute', 'runbook.status.test'],
    dataGenerator: () => ({
      id: generateId('execution-'),
      runbookId: generateId('runbook-'),
      alertId: generateId('alert-'),
      timestamp: new Date().toISOString(),
      status: randomItem(['started', 'in_progress', 'completed', 'failed']),
      steps: [
        {
          name: 'Check current connection pool settings',
          status: 'completed',
          output: 'max_connections=100'
        },
        {
          name: 'Verify active connections count',
          status: 'completed',
          output: 'active_connections=95'
        }
      ]
    })
  },
  {
    name: 'NOTEBOOKS',
    subjects: ['notebooks', 'notebooks.test'],
    dataGenerator: () => ({
      id: generateId('notebook-'),
      name: 'Database Performance Analysis',
      description: 'Analysis of database performance issues',
      created: new Date().toISOString(),
      updated: new Date().toISOString(),
      cells: [
        {
          type: 'markdown',
          content: '# Database Performance Analysis'
        },
        {
          type: 'code',
          language: 'bash',
          content: 'kubectl get pods -n database'
        }
      ]
    })
  },
  {
    name: 'NOTIFICATIONS',
    subjects: ['notifications', 'notification_requests'],
    dataGenerator: () => ({
      id: generateId('notification-'),
      timestamp: new Date().toISOString(),
      type: randomItem(['email', 'slack', 'pagerduty']),
      priority: randomItem(['low', 'medium', 'high', 'critical']),
      recipient: 'on-call-team',
      subject: 'Alert: Database Connection Issues',
      message: 'Database connection pool exhaustion detected in payment-service',
      metadata: {
        alertId: generateId('alert-'),
        service: 'payment-service',
        severity: 'critical'
      }
    })
  }
];

/**
 * Main function
 */
async function main() {
  console.log(`Test Data Publisher for Observability Agent`);
  console.log(`----------------------------------------------`);
  console.log(`NATS URL: ${config.natsUrl}`);
  if (config.specificStream) {
    console.log(`Publishing only to stream: ${config.specificStream}`);
  }
  console.log(`----------------------------------------------`);
  
  try {
    // Connect to NATS
    console.log(`Connecting to NATS server at ${config.natsUrl}...`);
    const nc = await connect({
      servers: config.natsUrl,
      timeout: 5000
    });
    
    console.log('Connected to NATS server');
    console.log(`Server information: ${nc.getServer()}`);
    
    // Create JetStream client
    const js = nc.jetstream();
    console.log('JetStream client created');
    
    // Filter streams if specific stream is requested
    const streamsToPublish = config.specificStream
      ? streamDefinitions.filter(s => s.name === config.specificStream.toUpperCase())
      : streamDefinitions;
    
    if (streamsToPublish.length === 0) {
      console.error(`Stream ${config.specificStream} not found`);
      await nc.drain();
      process.exit(1);
    }
    
    // Publish data to each stream
    for (const stream of streamsToPublish) {
      console.log(`\nPublishing to ${stream.name} stream...`);
      
      // Generate test data
      const data = stream.dataGenerator();
      
      // Publish to each subject
      for (const subject of stream.subjects) {
        try {
          // Publish data
          const ack = await js.publish(subject, sc.encode(JSON.stringify(data)));
          console.log(`Published to ${subject} (stream: ${stream.name}, seq: ${ack.seq})`);
          console.log(`Data: ${JSON.stringify(data, null, 2).substring(0, 100)}...`);
        } catch (error) {
          console.error(`Error publishing to ${subject}: ${error.message}`);
        }
      }
    }
    
    // Disconnect from NATS
    await nc.drain();
    console.log('\nDisconnected from NATS server');
    
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
