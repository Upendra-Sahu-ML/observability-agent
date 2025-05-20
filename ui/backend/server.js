const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
// NATS client
const { connect, StringCodec } = require('nats');
// Import alert functions
const { getHistoricalAlerts, getActiveAlerts } = require('./alerts');
// Import knowledge base functions
const { getIncidents, getPostmortems } = require('./knowledge');

// Configuration
const NATS_URL = process.env.NATS_URL || 'nats://nats:4222';
const sc = StringCodec(); // For encoding/decoding NATS messages

// In-memory cache for data
const cache = {
  agents: [],
  metrics: [],
  logs: [],
  deployment: [],
  rootcause: [],
  tracing: [],
  notification: [],
  postmortem: [],
  runbook: [],
  'alerts/history': [],
  'alerts/active': [],
  'knowledge/incidents': [],
  'knowledge/postmortems': []
};

// In-memory storage for runbook executions
const runbookExecutions = {};

// Cache TTL in milliseconds (5 minutes)
const CACHE_TTL = 5 * 60 * 1000;
const cacheTimestamps = {};

/**
 * Get data from cache or fetch from NATS
 * @param {string} type - The data type to fetch
 * @param {object} js - JetStream instance
 * @param {object} req - Express request object
 * @returns {Promise<Array>} - The requested data
 */
async function getData(type, js, req) {
  const now = Date.now();

  // Return cached data if it's fresh
  if (cache[type] && cacheTimestamps[type] && (now - cacheTimestamps[type] < CACHE_TTL)) {
    console.log(`Returning cached ${type} data`);
    return cache[type];
  }

  try {
    let data = [];

    // Different fetch strategies based on data type
    switch (type) {
      case 'agents':
        // Get agent status from NATS
        data = await getAgentStatus(js);
        break;

      case 'metrics':
        // Get metrics data, possibly filtered by service
        const service = req.query.service;
        data = await getMetricsData(js, service);
        break;

      case 'logs':
        // Get logs data, possibly filtered by service and time range
        const { service: logService, startTime, endTime } = req.query;
        data = await getLogsData(js, logService, startTime, endTime);
        break;

      case 'deployment':
        // Get deployment data
        data = await getDeploymentData(js);
        break;

      case 'rootcause':
        // Get root cause analysis results
        const alertId = req.query.alertId;
        data = await getRootCauseData(js, alertId);
        break;

      case 'tracing':
        // Get tracing data
        const { traceId, service: tracingService } = req.query;
        data = await getTracingData(js, traceId, tracingService);
        break;

      case 'notification':
        // Get notification data
        data = await getNotificationData(js);
        break;

      case 'postmortem':
        // Get postmortem reports
        data = await getPostmortemData(js);
        break;

      case 'runbook':
        // Get runbook information
        const runbookId = req.query.id;
        data = await getRunbookData(js, runbookId);
        break;

      case 'alerts/history':
        // Get historical alerts
        data = await getHistoricalAlerts(js);
        break;

      case 'alerts/active':
        // Get active alerts
        data = await getActiveAlerts(js);
        break;

      case 'knowledge/incidents':
        // Get incidents from knowledge base
        data = await getIncidents(js);
        break;

      case 'knowledge/postmortems':
        // Get postmortems from knowledge base
        data = await getPostmortems(js);
        break;

      default:
        data = [];
    }

    // Update cache
    cache[type] = data;
    cacheTimestamps[type] = now;

    return data;
  } catch (error) {
    console.error(`Error fetching ${type} data:`, error);
    // Return cached data if available, even if stale
    return cache[type] || [];
  }
}

/**
 * Get agent status information
 * @param {object} js - JetStream instance
 * @returns {Promise<Array>} - Agent status data
 */
async function getAgentStatus(js) {
  try {
    // In a real implementation, you would query NATS for agent status
    // For now, return mock data with agent statuses
    return [
      { id: 'metric-agent', name: 'Metric Agent', status: 'active', lastSeen: new Date().toISOString() },
      { id: 'log-agent', name: 'Log Agent', status: 'active', lastSeen: new Date().toISOString() },
      { id: 'deployment-agent', name: 'Deployment Agent', status: 'active', lastSeen: new Date().toISOString() },
      { id: 'tracing-agent', name: 'Tracing Agent', status: 'active', lastSeen: new Date().toISOString() },
      { id: 'root-cause-agent', name: 'Root Cause Agent', status: 'active', lastSeen: new Date().toISOString() },
      { id: 'notification-agent', name: 'Notification Agent', status: 'active', lastSeen: new Date().toISOString() },
      { id: 'postmortem-agent', name: 'Postmortem Agent', status: 'active', lastSeen: new Date().toISOString() },
      { id: 'runbook-agent', name: 'Runbook Agent', status: 'active', lastSeen: new Date().toISOString() }
    ];
  } catch (error) {
    console.error('Error getting agent status:', error);
    return [];
  }
}

/**
 * Get metrics data
 * @param {object} js - JetStream instance
 * @param {string} service - Optional service filter
 * @returns {Promise<Array>} - Metrics data
 */
async function getMetricsData(js, service) {
  try {
    // Mock metrics data
    const metrics = [
      { name: 'CPU Usage', value: '45%', timestamp: new Date().toISOString(), service: 'payment-service' },
      { name: 'Memory Usage', value: '1.2GB', timestamp: new Date().toISOString(), service: 'payment-service' },
      { name: 'Request Rate', value: '120 req/s', timestamp: new Date().toISOString(), service: 'payment-service' },
      { name: 'Error Rate', value: '0.5%', timestamp: new Date().toISOString(), service: 'payment-service' },
      { name: 'CPU Usage', value: '30%', timestamp: new Date().toISOString(), service: 'order-service' },
      { name: 'Memory Usage', value: '800MB', timestamp: new Date().toISOString(), service: 'order-service' },
      { name: 'Request Rate', value: '85 req/s', timestamp: new Date().toISOString(), service: 'order-service' },
      { name: 'Error Rate', value: '0.2%', timestamp: new Date().toISOString(), service: 'order-service' }
    ];

    // Filter by service if provided
    return service ? metrics.filter(m => m.service === service) : metrics;
  } catch (error) {
    console.error('Error getting metrics data:', error);
    return [];
  }
}

/**
 * Get logs data
 * @param {object} js - JetStream instance
 * @param {string} service - Optional service filter
 * @param {string} startTime - Optional start time filter
 * @param {string} endTime - Optional end time filter
 * @returns {Promise<Array>} - Logs data
 */
async function getLogsData(js, service, startTime, endTime) {
  try {
    // Mock logs data
    const logs = [
      { timestamp: '2023-08-15T10:30:45Z', level: 'INFO', message: 'Application started', service: 'payment-service' },
      { timestamp: '2023-08-15T10:31:12Z', level: 'ERROR', message: 'Database connection failed', service: 'payment-service' },
      { timestamp: '2023-08-15T10:32:05Z', level: 'INFO', message: 'Database connection restored', service: 'payment-service' },
      { timestamp: '2023-08-15T10:35:22Z', level: 'WARN', message: 'High memory usage detected', service: 'order-service' },
      { timestamp: '2023-08-15T10:40:18Z', level: 'INFO', message: 'Processing order #12345', service: 'order-service' }
    ];

    // Apply filters if provided
    let filteredLogs = logs;

    if (service) {
      filteredLogs = filteredLogs.filter(log => log.service === service);
    }

    if (startTime) {
      const start = new Date(startTime);
      filteredLogs = filteredLogs.filter(log => new Date(log.timestamp) >= start);
    }

    if (endTime) {
      const end = new Date(endTime);
      filteredLogs = filteredLogs.filter(log => new Date(log.timestamp) <= end);
    }

    return filteredLogs;
  } catch (error) {
    console.error('Error getting logs data:', error);
    return [];
  }
}

/**
 * Get deployment data
 * @param {object} js - JetStream instance
 * @returns {Promise<Array>} - Deployment data
 */
async function getDeploymentData(js) {
  try {
    // Mock deployment data
    return [
      { id: 'deploy-1', service: 'payment-service', version: 'v1.2.3', status: 'deployed', timestamp: '2023-08-14T15:30:00Z' },
      { id: 'deploy-2', service: 'order-service', version: 'v2.0.1', status: 'deployed', timestamp: '2023-08-15T09:45:00Z' },
      { id: 'deploy-3', service: 'inventory-service', version: 'v1.5.0', status: 'failed', timestamp: '2023-08-15T11:20:00Z' }
    ];
  } catch (error) {
    console.error('Error getting deployment data:', error);
    return [];
  }
}

/**
 * Get root cause analysis data
 * @param {object} js - JetStream instance
 * @param {string} alertId - Optional alert ID filter
 * @returns {Promise<Array>} - Root cause analysis data
 */
async function getRootCauseData(js, alertId) {
  try {
    // Mock root cause data
    const rootCauses = [
      {
        id: 'rc-1',
        alertId: 'alert-123',
        service: 'payment-service',
        cause: 'Database connection pool exhaustion',
        confidence: 0.92,
        timestamp: '2023-08-15T10:35:00Z',
        details: 'The payment service experienced high traffic which exhausted the database connection pool.'
      },
      {
        id: 'rc-2',
        alertId: 'alert-456',
        service: 'order-service',
        cause: 'Memory leak in order processing',
        confidence: 0.85,
        timestamp: '2023-08-15T11:20:00Z',
        details: 'A memory leak was detected in the order processing component, causing gradual performance degradation.'
      }
    ];

    // Filter by alert ID if provided
    return alertId ? rootCauses.filter(rc => rc.alertId === alertId) : rootCauses;
  } catch (error) {
    console.error('Error getting root cause data:', error);
    return [];
  }
}

/**
 * Get tracing data
 * @param {object} js - JetStream instance
 * @param {string} traceId - Optional trace ID filter
 * @param {string} service - Optional service filter
 * @returns {Promise<Array>} - Tracing data
 */
async function getTracingData(js, traceId, service) {
  try {
    // Mock tracing data
    const traces = [
      {
        id: 'trace-1',
        service: 'api-gateway',
        operation: 'POST /api/orders',
        duration: 250,
        timestamp: '2023-08-15T10:30:00Z',
        spans: [
          { id: 'span-1', service: 'api-gateway', operation: 'handleRequest', duration: 10 },
          { id: 'span-2', service: 'order-service', operation: 'createOrder', duration: 150 },
          { id: 'span-3', service: 'payment-service', operation: 'processPayment', duration: 90 }
        ]
      },
      {
        id: 'trace-2',
        service: 'api-gateway',
        operation: 'GET /api/products',
        duration: 120,
        timestamp: '2023-08-15T10:32:00Z',
        spans: [
          { id: 'span-4', service: 'api-gateway', operation: 'handleRequest', duration: 5 },
          { id: 'span-5', service: 'inventory-service', operation: 'getProducts', duration: 115 }
        ]
      }
    ];

    // Apply filters
    let filteredTraces = traces;

    if (traceId) {
      filteredTraces = filteredTraces.filter(trace => trace.id === traceId);
    }

    if (service) {
      filteredTraces = filteredTraces.filter(trace =>
        trace.service === service || trace.spans.some(span => span.service === service)
      );
    }

    return filteredTraces;
  } catch (error) {
    console.error('Error getting tracing data:', error);
    return [];
  }
}

/**
 * Get notification data
 * @param {object} js - JetStream instance
 * @returns {Promise<Array>} - Notification data
 */
async function getNotificationData(js) {
  try {
    // Mock notification data
    return [
      {
        id: 'notif-1',
        alertId: 'alert-123',
        channel: 'slack',
        recipient: '#incidents',
        message: 'High CPU usage detected in payment-service',
        status: 'sent',
        timestamp: '2023-08-15T10:35:00Z'
      },
      {
        id: 'notif-2',
        alertId: 'alert-456',
        channel: 'email',
        recipient: 'oncall@example.com',
        message: 'Memory leak detected in order-service',
        status: 'sent',
        timestamp: '2023-08-15T11:20:00Z'
      }
    ];
  } catch (error) {
    console.error('Error getting notification data:', error);
    return [];
  }
}

/**
 * Get postmortem data
 * @param {object} js - JetStream instance
 * @returns {Promise<Array>} - Postmortem data
 */
async function getPostmortemData(js) {
  try {
    // Mock postmortem data
    return [
      {
        id: 'pm-1',
        alertId: 'alert-123',
        title: 'Payment Service Outage - August 15',
        status: 'completed',
        createdAt: '2023-08-15T14:00:00Z',
        summary: 'The payment service experienced an outage due to database connection pool exhaustion.',
        impact: 'Approximately 500 users were unable to complete payments for 15 minutes.',
        rootCause: 'Database connection pool exhaustion due to traffic spike.',
        resolution: 'Increased connection pool size and implemented better connection management.',
        actionItems: [
          'Implement connection pool monitoring',
          'Add auto-scaling for the payment service',
          'Improve error handling for database connection failures'
        ]
      }
    ];
  } catch (error) {
    console.error('Error getting postmortem data:', error);
    return [];
  }
}

/**
 * Get runbook data
 * @param {object} js - JetStream instance
 * @param {string} runbookId - Optional runbook ID filter
 * @returns {Promise<Array>} - Runbook data
 */
async function getRunbookData(js, runbookId) {
  try {
    // If JetStream is available, try to get runbooks from there
    if (js) {
      try {
        let streamExists = false;
        let consumer = null;
        let messages = [];

        // Check if RUNBOOKS stream exists using our wrapper
        try {
          await js.streamInfo('RUNBOOKS');
          streamExists = true;

          // Get consumer using our wrapper
          try {
            consumer = await js.getConsumer('RUNBOOKS', 'runbook-viewer');

            // Handle different consumer fetch APIs
            if (typeof consumer.fetch === 'function') {
              if (consumer.fetch.length > 0) {
                // Newer API expects an options object
                messages = await consumer.fetch({ max_messages: 100 });
              } else {
                // Older API expects a number
                messages = await consumer.fetch(100);
              }
            }
          } catch (consErr) {
            console.log('Consumer not found:', consErr.message);

            // Try to create the consumer
            try {
              const consumerConfig = {
                durable_name: 'runbook-viewer',
                ack_policy: 'explicit',
                deliver_policy: 'all'
              };

              consumer = await js.addConsumer('RUNBOOKS', consumerConfig);
              console.log('Created runbook-viewer consumer');

              // Try to fetch messages again
              if (typeof consumer.fetch === 'function') {
                if (consumer.fetch.length > 0) {
                  messages = await consumer.fetch({ max_messages: 100 });
                } else {
                  messages = await consumer.fetch(100);
                }
              }
            } catch (createErr) {
              console.error('Error creating consumer:', createErr.message);
            }
          }
        } catch (err) {
          console.log('Stream not found:', err.message);

          // Try to create the stream
          try {
            const streamConfig = {
              name: 'RUNBOOKS',
              subjects: ['runbooks.*']
            };

            await js.addStream(streamConfig);
            console.log('Created RUNBOOKS stream');
            streamExists = true;
          } catch (createErr) {
            console.error('Error creating stream:', createErr.message);
          }
        }

        if (streamExists && messages && messages.length > 0) {
          const runbooks = messages.map(msg => {
            const data = JSON.parse(typeof msg.data === 'string' ? msg.data : msg.data.toString());
            msg.ack();
            return data;
          });

          // Filter by runbook ID if provided
          return runbookId ? runbooks.filter(rb => rb.id === runbookId) : runbooks;
        }
      } catch (err) {
        console.warn(`Error fetching runbooks from JetStream: ${err.message}`);
        // Fall back to mock data
      }
    }

    // Mock runbook data as fallback
    const runbooks = [
      {
        id: 'rb-1',
        title: 'Database Connection Issues',
        service: 'payment-service',
        steps: [
          'Check database connection pool settings',
          'Verify database server is running',
          'Check for network connectivity issues',
          'Restart the payment service if necessary'
        ],
        createdAt: '2023-07-10T09:00:00Z',
        updatedAt: '2023-08-01T14:30:00Z'
      },
      {
        id: 'rb-2',
        title: 'Memory Leak Remediation',
        service: 'order-service',
        steps: [
          'Take heap dump of the affected service',
          'Analyze memory usage patterns',
          'Identify objects with unusual retention',
          'Apply fix to release references properly',
          'Restart the service with the fix'
        ],
        createdAt: '2023-07-15T11:00:00Z',
        updatedAt: '2023-08-05T16:45:00Z'
      }
    ];

    // Filter by runbook ID if provided
    return runbookId ? runbooks.filter(rb => rb.id === runbookId) : runbooks;
  } catch (error) {
    console.error('Error getting runbook data:', error);
    return [];
  }
}

/**
 * Execute a runbook
 * @param {object} js - JetStream instance
 * @param {string} runbookId - ID of the runbook to execute
 * @returns {Promise<object>} - Execution details
 */
async function executeRunbook(js, runbookId) {
  try {
    // Generate a unique execution ID
    const executionId = `exec-${Date.now()}-${Math.floor(Math.random() * 1000)}`;

    // Get the runbook
    const runbooks = await getRunbookData(js, runbookId);
    if (!runbooks || runbooks.length === 0) {
      throw new Error(`Runbook with ID ${runbookId} not found`);
    }

    const runbook = runbooks[0];

    // Create execution record
    runbookExecutions[executionId] = {
      executionId,
      runbookId,
      status: 'starting',
      progress: 0,
      startTime: new Date().toISOString(),
      steps: runbook.steps.map((step, index) => ({
        step_number: index + 1,
        description: step,
        status: 'pending',
        outcome: null
      })),
      currentStep: 0
    };

    // Try to send execution request to runbook agent via JetStream
    let usedRealExecution = false;

    if (js) {
      try {
        // Prepare execution request
        const executionRequest = {
          executionId,
          runbookId,
          runbook,
          timestamp: new Date().toISOString()
        };

        // Use our wrapper to publish
        try {
          await js.publish('runbook.execute', sc.encode(JSON.stringify(executionRequest)));
          usedRealExecution = true;
          console.log(`Published runbook execution request to runbook.execute: ${executionId}`);

          // Set up a subscription to receive execution updates
          setupExecutionSubscription(executionId);
        } catch (pubErr) {
          console.warn(`Error publishing with JetStream: ${pubErr.message}. Trying regular NATS publish.`);

          // Fallback to regular NATS publish
          if (nc && typeof nc.publish === 'function') {
            nc.publish('runbook.execute', sc.encode(JSON.stringify(executionRequest)));
            usedRealExecution = true;
            console.log(`Published runbook execution request using regular NATS: ${executionId}`);

            // Set up a subscription to receive execution updates
            setupExecutionSubscription(executionId);
          } else {
            throw new Error('Neither JetStream nor regular NATS publish is available');
          }
        }
      } catch (err) {
        console.warn(`Error publishing execution request: ${err.message}. Falling back to simulation.`);
        // Fall back to simulation
        usedRealExecution = false;
      }
    }

    // If real execution wasn't used, simulate execution in the background
    if (!usedRealExecution) {
      console.log(`Using simulated execution for runbook: ${runbookId}`);
      simulateRunbookExecution(executionId, runbook);
    }

    return {
      executionId,
      runbookId,
      status: 'starting',
      message: 'Runbook execution started',
      mode: usedRealExecution ? 'real' : 'simulated'
    };
  } catch (error) {
    console.error('Error executing runbook:', error);
    throw error;
  }
}

/**
 * Set up a subscription to receive execution updates
 * @param {string} executionId - ID of the execution to track
 */
function setupExecutionSubscription(executionId) {
  if (!nc) return;

  try {
    // Subscribe to execution updates
    const sub = nc.subscribe(`runbook.status.${executionId}`);
    console.log(`Subscribed to runbook.status.${executionId}`);

    // Process incoming messages
    (async () => {
      for await (const msg of sub) {
        try {
          const update = JSON.parse(sc.decode(msg.data));
          console.log(`Received execution update for ${executionId}:`, update);

          // Update the execution record
          if (runbookExecutions[executionId]) {
            runbookExecutions[executionId] = {
              ...runbookExecutions[executionId],
              ...update,
              lastUpdated: new Date().toISOString()
            };
          }

          // If execution is complete or failed, unsubscribe
          if (update.status === 'completed' || update.status === 'failed') {
            await sub.unsubscribe();
            console.log(`Unsubscribed from runbook.status.${executionId}`);
          }
        } catch (err) {
          console.error(`Error processing execution update: ${err.message}`);
        }
      }
    })().catch(err => {
      console.error(`Subscription error: ${err.message}`);
    });
  } catch (err) {
    console.error(`Error setting up execution subscription: ${err.message}`);
  }
}

/**
 * Simulate runbook execution
 * @param {string} executionId - ID of the execution
 * @param {object} runbook - Runbook to execute
 */
function simulateRunbookExecution(executionId, runbook) {
  const execution = runbookExecutions[executionId];
  if (!execution) return;

  // Update status to in_progress
  execution.status = 'in_progress';
  execution.progress = 5;

  // Simulate execution of each step
  const totalSteps = runbook.steps.length;
  let currentStep = 0;

  const stepInterval = setInterval(() => {
    if (!runbookExecutions[executionId]) {
      clearInterval(stepInterval);
      return;
    }

    const execution = runbookExecutions[executionId];

    // Execute current step
    execution.steps[currentStep].status = 'in_progress';
    execution.currentStep = currentStep;

    // After a delay, complete the step
    setTimeout(() => {
      if (!runbookExecutions[executionId]) {
        clearInterval(stepInterval);
        return;
      }

      execution.steps[currentStep].status = 'completed';
      execution.steps[currentStep].outcome = 'Step completed successfully';

      // Update progress
      execution.progress = Math.round(((currentStep + 1) / totalSteps) * 100);

      // Move to next step or complete
      currentStep++;

      if (currentStep >= totalSteps) {
        // All steps completed
        execution.status = 'completed';
        execution.endTime = new Date().toISOString();
        clearInterval(stepInterval);
      }
    }, 3000); // Each step takes 3 seconds

  }, 5000); // 5 seconds between steps
}

/**
 * Get runbook execution status
 * @param {string} executionId - ID of the execution
 * @returns {object} - Execution status
 */
function getRunbookExecutionStatus(executionId) {
  const execution = runbookExecutions[executionId];
  if (!execution) {
    throw new Error(`Execution with ID ${executionId} not found`);
  }

  return {
    executionId,
    runbookId: execution.runbookId,
    status: execution.status,
    progress: execution.progress,
    startTime: execution.startTime,
    endTime: execution.endTime,
    steps: execution.steps,
    currentStep: execution.currentStep
  };
}

/**
 * Add a new runbook
 * @param {object} js - JetStream instance
 * @param {object} runbookData - Runbook data to add
 * @returns {Promise<object>} - Result of the operation
 */
async function addRunbook(js, runbookData) {
  try {
    if (!js) {
      throw new Error('NATS JetStream not available');
    }

    // Generate ID if not provided
    const runbook = {
      id: runbookData.id || `rb-${Date.now()}`,
      title: runbookData.name,
      service: runbookData.service || '',
      steps: parseRunbookSteps(runbookData.content),
      content: runbookData.content,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };

    // Ensure RUNBOOKS stream exists
    try {
      await js.streams.info('RUNBOOKS').catch(() => {
        // Create stream if it doesn't exist
        return js.streams.add({
          name: 'RUNBOOKS',
          subjects: ['runbooks.*']
        });
      });

      // Ensure consumer exists
      await js.consumers.info('RUNBOOKS', 'runbook-viewer').catch(() => {
        // Create consumer if it doesn't exist
        return js.consumers.add('RUNBOOKS', {
          durable_name: 'runbook-viewer',
          ack_policy: 'explicit',
          deliver_policy: 'all'
        });
      });
    } catch (err) {
      console.error('Error setting up RUNBOOKS stream:', err);
      throw new Error('Failed to set up RUNBOOKS stream');
    }

    // Publish runbook to JetStream
    await js.publish(`runbooks.${runbook.id}`, JSON.stringify(runbook));

    return { success: true, runbook };
  } catch (error) {
    console.error('Error adding runbook:', error);
    throw error;
  }
}

/**
 * Sync runbooks from external source
 * @param {object} js - JetStream instance
 * @param {object} syncData - Sync configuration
 * @returns {Promise<object>} - Result of the operation
 */
async function syncRunbooks(js, syncData) {
  try {
    if (!js) {
      throw new Error('NATS JetStream not available');
    }

    if (syncData.source === 'github') {
      // Validate required fields
      if (!syncData.repo) {
        throw new Error('GitHub repository is required');
      }

      // In a real implementation, this would call the GitHub API to fetch runbooks
      // For this example, we'll simulate a successful sync

      // Create some sample runbooks
      const runbooks = [
        {
          id: `rb-github-${Date.now()}-1`,
          title: 'High CPU Usage',
          service: 'api-gateway',
          steps: [
            'Check system load',
            'Identify CPU-intensive processes',
            'Scale up the service if needed',
            'Optimize code if possible'
          ],
          content: '# High CPU Usage\n\n1. Check system load\n2. Identify CPU-intensive processes\n3. Scale up the service if needed\n4. Optimize code if possible',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          source: `github:${syncData.repo}`
        },
        {
          id: `rb-github-${Date.now()}-2`,
          title: 'Database Connection Pool Exhaustion',
          service: 'payment-service',
          steps: [
            'Check connection pool metrics',
            'Verify connection leaks',
            'Increase pool size temporarily',
            'Fix connection handling in code'
          ],
          content: '# Database Connection Pool Exhaustion\n\n1. Check connection pool metrics\n2. Verify connection leaks\n3. Increase pool size temporarily\n4. Fix connection handling in code',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          source: `github:${syncData.repo}`
        }
      ];

      // Ensure RUNBOOKS stream exists
      await js.streams.info('RUNBOOKS').catch(() => {
        // Create stream if it doesn't exist
        return js.streams.add({
          name: 'RUNBOOKS',
          subjects: ['runbooks.*']
        });
      });

      // Publish runbooks to JetStream
      for (const runbook of runbooks) {
        await js.publish(`runbooks.${runbook.id}`, JSON.stringify(runbook));
      }

      return { success: true, count: runbooks.length };
    } else {
      throw new Error(`Unsupported sync source: ${syncData.source}`);
    }
  } catch (error) {
    console.error('Error syncing runbooks:', error);
    throw error;
  }
}

/**
 * Parse runbook steps from markdown content
 * @param {string} content - Markdown content
 * @returns {Array<string>} - Array of steps
 */
function parseRunbookSteps(content) {
  if (!content) return [];

  const steps = [];
  const lines = content.split('\n');

  // Simple parser for numbered lists and bullet points
  for (const line of lines) {
    const trimmedLine = line.trim();
    // Match numbered lists (1. Step one)
    if (/^\d+\.\s+.+/.test(trimmedLine)) {
      steps.push(trimmedLine.replace(/^\d+\.\s+/, ''));
    }
    // Match bullet points (- Step one or * Step one)
    else if (/^[-*]\s+.+/.test(trimmedLine)) {
      steps.push(trimmedLine.replace(/^[-*]\s+/, ''));
    }
  }

  return steps;
}

async function start() {
  let nc = null;
  let js = null;

  // Set up Express app
  const app = express();
  app.use(cors());
  app.use(bodyParser.json());

  try {
    // Try to connect to NATS
    console.log(`Attempting to connect to NATS at ${NATS_URL}...`);

    // Add more detailed logging
    console.log('NATS connection options:', {
      servers: NATS_URL,
      timeout: 5000,
      debug: process.env.DEBUG === 'true'
    });

    nc = await connect({
      servers: NATS_URL,
      timeout: 5000,
      debug: process.env.DEBUG === 'true'
    }).catch(err => {
      console.warn(`NATS connection failed: ${err.message}. Will use mock data only.`);
      console.error('NATS connection error details:', err);
      return null;
    });

    if (nc) {
      console.log('Connected to NATS');
      console.log('NATS connection state:', nc.info);

      // Initialize JetStream
      try {
        if (typeof nc.jetstream === 'function') {
          js = nc.jetstream();
          console.log('JetStream initialized');

          // Try to detect JetStream API version
          if (js) {
            // Create a wrapper around the JetStream object to handle different API versions
            const jsWrapper = {
              _js: js,

              // Method to get stream info
              async streamInfo(streamName) {
                if (typeof js.streams === 'object' && typeof js.streams.info === 'function') {
                  console.log('Using newer JetStream API (streams.info)');
                  return js.streams.info(streamName);
                } else if (typeof js.streamInfo === 'function') {
                  console.log('Using older JetStream API (streamInfo)');
                  return js.streamInfo(streamName);
                } else {
                  throw new Error('JetStream API does not support stream info');
                }
              },

              // Method to add a stream
              async addStream(config) {
                if (typeof js.streams === 'object' && typeof js.streams.add === 'function') {
                  console.log('Using newer JetStream API (streams.add)');
                  return js.streams.add(config);
                } else if (typeof js.addStream === 'function') {
                  console.log('Using older JetStream API (addStream)');
                  return js.addStream(config);
                } else {
                  throw new Error('JetStream API does not support adding streams');
                }
              },

              // Method to get a consumer
              async getConsumer(streamName, consumerName) {
                if (typeof js.consumers === 'object' && typeof js.consumers.get === 'function') {
                  console.log('Using newer JetStream API (consumers.get)');
                  return js.consumers.get(streamName, consumerName);
                } else if (typeof js.consumer === 'function') {
                  console.log('Using older JetStream API (consumer)');
                  return js.consumer(streamName, { durable_name: consumerName });
                } else {
                  throw new Error('JetStream API does not support getting consumers');
                }
              },

              // Method to add a consumer
              async addConsumer(streamName, config) {
                if (typeof js.consumers === 'object' && typeof js.consumers.add === 'function') {
                  console.log('Using newer JetStream API (consumers.add)');
                  return js.consumers.add(streamName, config);
                } else if (typeof js.addConsumer === 'function') {
                  console.log('Using older JetStream API (addConsumer)');
                  return js.addConsumer(streamName, config);
                } else {
                  throw new Error('JetStream API does not support adding consumers');
                }
              },

              // Method to publish a message
              async publish(subject, data) {
                if (typeof js.publish === 'function') {
                  console.log('Using JetStream publish');
                  return js.publish(subject, data);
                } else {
                  console.log('Falling back to regular NATS publish');
                  return nc.publish(subject, data);
                }
              }
            };

            // Replace the original js object with our wrapper
            js = jsWrapper;
            console.log('Created JetStream API compatibility wrapper');
          }
        } else {
          console.log('JetStream not available in this NATS client version');
          js = null;
        }
      } catch (jsErr) {
        console.error(`JetStream initialization error: ${jsErr.message}`);
        js = null;
      }
    } else {
      console.log('Running in mock data mode (no NATS connection)');
    }
  } catch (err) {
    console.warn(`NATS setup error: ${err.message}. Will use mock data only.`);
    console.error('NATS setup error details:', err);
  }

  // Health check endpoint
  app.get('/health', (_, res) => {
    res.json({
      status: 'healthy',
      nats: nc ? 'connected' : 'disconnected',
      jetstream: js ? 'available' : 'unavailable',
      mode: nc ? 'connected' : 'mock',
      uptime: process.uptime()
    });
  });

  // API endpoints
  const routes = [
    'agents', 'metrics', 'logs', 'deployment', 'rootcause',
    'tracing', 'notification', 'postmortem', 'runbook'
  ];

  routes.forEach(route => {
    app.get(`/api/${route}`, async (req, res) => {
      try {
        const data = await getData(route, js, req);
        res.json(data);
      } catch (error) {
        console.error(`Error handling ${route} request:`, error);
        res.status(500).json({ error: `Failed to fetch ${route} data` });
      }
    });
  });

  // Alert endpoints
  app.get('/api/alerts/history', async (req, res) => {
    try {
      const data = await getData('alerts/history', js, req);
      res.json(data);
    } catch (error) {
      console.error('Error handling alerts/history request:', error);
      res.status(500).json({ error: 'Failed to fetch historical alerts' });
    }
  });

  app.get('/api/alerts/active', async (req, res) => {
    try {
      const data = await getData('alerts/active', js, req);
      res.json(data);
    } catch (error) {
      console.error('Error handling alerts/active request:', error);
      res.status(500).json({ error: 'Failed to fetch active alerts' });
    }
  });

  // Knowledge base endpoints
  app.get('/api/knowledge/incidents', async (req, res) => {
    try {
      const data = await getData('knowledge/incidents', js, req);
      res.json(data);
    } catch (error) {
      console.error('Error handling knowledge/incidents request:', error);
      res.status(500).json({ error: 'Failed to fetch incidents from knowledge base' });
    }
  });

  app.get('/api/knowledge/postmortems', async (req, res) => {
    try {
      const data = await getData('knowledge/postmortems', js, req);
      res.json(data);
    } catch (error) {
      console.error('Error handling knowledge/postmortems request:', error);
      res.status(500).json({ error: 'Failed to fetch postmortems from knowledge base' });
    }
  });

  // Runbook management endpoints

  // Add a new runbook
  app.post('/api/runbook', async (req, res) => {
    try {
      const result = await addRunbook(js, req.body);
      res.json(result);
    } catch (error) {
      console.error('Error adding runbook:', error);
      res.status(500).json({ error: error.message || 'Failed to add runbook' });
    }
  });

  // Execute a runbook
  app.post('/api/runbook/execute', async (req, res) => {
    try {
      const { runbookId } = req.body;
      if (!runbookId) {
        return res.status(400).json({ error: 'Runbook ID is required' });
      }

      const result = await executeRunbook(js, runbookId);
      res.json(result);
    } catch (error) {
      console.error('Error executing runbook:', error);
      res.status(500).json({ error: error.message || 'Failed to execute runbook' });
    }
  });

  // Get runbook execution status
  app.get('/api/runbook/status/:executionId', (req, res) => {
    try {
      const { executionId } = req.params;
      if (!executionId) {
        return res.status(400).json({ error: 'Execution ID is required' });
      }

      const status = getRunbookExecutionStatus(executionId);
      res.json(status);
    } catch (error) {
      console.error('Error getting execution status:', error);
      res.status(500).json({ error: error.message || 'Failed to get execution status' });
    }
  });

  // Sync runbooks from external source
  app.post('/api/runbook/sync', async (req, res) => {
    try {
      const result = await syncRunbooks(js, req.body);
      res.json(result);
    } catch (error) {
      console.error('Error syncing runbooks:', error);
      res.status(500).json({ error: error.message || 'Failed to sync runbooks' });
    }
  });

  // Start the server
  const port = process.env.PORT || 5000;
  app.listen(port, () => console.log(`UI backend listening on port ${port}`));

  // Handle graceful shutdown
  process.on('SIGINT', async () => {
    console.log('Shutting down...');
    if (nc) {
      await nc.close();
    }
    process.exit(0);
  });
}

start();