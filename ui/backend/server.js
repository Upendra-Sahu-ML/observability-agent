const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const axios = require('axios');
// NATS client
const { connect, StringCodec } = require('nats');
// Import alert functions
const { getHistoricalAlerts, getActiveAlerts } = require('./alerts');
// Import knowledge base functions
const { getIncidents, getPostmortems } = require('./knowledge');

// Configuration
const NATS_URL = process.env.NATS_URL || 'nats://nats:4222';
// Removed NATS_DOMAIN to use default domain
const sc = StringCodec(); // For encoding/decoding NATS messages

// Import constants
const { STREAM_NAMES, CONSUMER_NAMES, checkStreamExists, createConsumer } = require('./constants');

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
 * @param {object} nc - NATS connection
 * @param {object} req - Express request object
 * @returns {Promise<Array>} - The requested data
 */
async function getData(type, js, nc, req) {
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
        data = await getAgentStatus(js, nc);
        break;

      case 'metrics':
        // Get metrics data, possibly filtered by service
        const service = req.query.service;
        data = await getMetricsData(js, nc, service);
        break;

      case 'logs':
        // Get logs data, possibly filtered by service and time range
        const { service: logService, startTime, endTime } = req.query;
        data = await getLogsData(js, nc, logService, startTime, endTime);
        break;

      case 'deployment':
        // Get deployment data
        data = await getDeploymentData(js, nc);
        break;

      case 'rootcause':
        // Get root cause analysis results
        const alertId = req.query.alertId;
        data = await getRootCauseData(js, nc, alertId);
        break;

      case 'tracing':
        // Get tracing data
        const { traceId, service: tracingService } = req.query;
        data = await getTracingData(js, nc, traceId, tracingService);
        break;

      case 'notification':
        // Get notification data
        data = await getNotificationData(js, nc);
        break;

      case 'postmortem':
        // Get postmortem reports
        data = await getPostmortemData(js, nc);
        break;

      case 'runbook':
        // Get runbook information
        const runbookId = req.query.id;
        data = await getRunbookData(js, nc, runbookId);
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
 * @param {object} nc - NATS connection
 * @returns {Promise<Array>} - Agent status data
 */
async function getAgentStatus(js, nc) {
  try {
    // Default agent list to ensure we always return something
    const defaultAgents = [
      { id: 'metric-agent', name: 'Metric Agent', status: 'unknown', lastSeen: null },
      { id: 'log-agent', name: 'Log Agent', status: 'unknown', lastSeen: null },
      { id: 'deployment-agent', name: 'Deployment Agent', status: 'unknown', lastSeen: null },
      { id: 'tracing-agent', name: 'Tracing Agent', status: 'unknown', lastSeen: null },
      { id: 'root-cause-agent', name: 'Root Cause Agent', status: 'unknown', lastSeen: null },
      { id: 'notification-agent', name: 'Notification Agent', status: 'unknown', lastSeen: null },
      { id: 'postmortem-agent', name: 'Postmortem Agent', status: 'unknown', lastSeen: null },
      { id: 'runbook-agent', name: 'Runbook Agent', status: 'unknown', lastSeen: null }
    ];

    // If no JetStream or NATS connection, return default agents with unknown status
    if (!js || !nc) {
      console.warn('NATS not available, returning default agent list with unknown status');
      return defaultAgents;
    }

    // Get JetStreamManager from the wrapper if available
    const jsm = js._jsm || null;

    if (!jsm) {
      console.warn('JetStreamManager not available, returning default agent list');
      return defaultAgents;
    }

    // Check if AGENTS stream exists using JetStreamManager
    let streamExists = false;
    try {
      await jsm.streams.info(STREAM_NAMES.AGENTS);
      streamExists = true;
    } catch (err) {
      streamExists = false;
    }

    // If stream doesn't exist, try to create it
    if (!streamExists) {
      try {
        await jsm.streams.add({
          name: STREAM_NAMES.AGENTS,
          subjects: ['agent.status.*', 'agent.status.>']
        });
        streamExists = true;
        console.log(`Created ${STREAM_NAMES.AGENTS} stream using JetStreamManager`);
      } catch (createErr) {
        console.error(`Error creating ${STREAM_NAMES.AGENTS} stream: ${createErr.message}`);
      }
    }

    if (!streamExists) {
      return defaultAgents;
    }

    // Create a consumer for the AGENTS stream using the utility function
    let consumer;
    try {
      consumer = await createConsumer(jsm, js, STREAM_NAMES.AGENTS, CONSUMER_NAMES.AGENTS);
    } catch (err) {
      console.error(`Error creating consumer for ${STREAM_NAMES.AGENTS}: ${err.message}`);
      return defaultAgents;
    }

    // Fetch agent status messages
    let messages = [];
    try {
      const fetchOptions = { max_messages: 100 };
      if (typeof consumer.fetch === 'function') {
        messages = await consumer.fetch(fetchOptions);
      } else if (typeof consumer.pull === 'function') {
        messages = await consumer.pull(fetchOptions.max_messages);
      } else {
        throw new Error('Consumer does not support fetch or pull');
      }
    } catch (err) {
      console.error(`Error fetching messages: ${err.message}`);
      return defaultAgents;
    }

    // Process messages and update agent status
    const agentStatus = {};
    for (const msg of messages) {
      try {
        const data = JSON.parse(sc.decode(msg.data));
        const agentId = data.id || data.agent_id;

        if (agentId) {
          agentStatus[agentId] = {
            id: agentId,
            name: data.name || agentId,
            status: data.status || 'active',
            lastSeen: data.timestamp || new Date().toISOString()
          };
        }

        // Acknowledge the message
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      } catch (err) {
        console.error(`Error processing agent status message: ${err.message}`);
        // Try to acknowledge the message even if processing failed
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      }
    }

    // Merge with default agents to ensure we return all expected agents
    const result = defaultAgents.map(defaultAgent => {
      return agentStatus[defaultAgent.id] || defaultAgent;
    });

    return result;
  } catch (error) {
    console.error('Error getting agent status:', error);
    return [];
  }
}

/**
 * Get metrics data
 * @param {object} js - JetStream instance
 * @param {object} nc - NATS connection
 * @param {string} service - Optional service filter
 * @returns {Promise<Array>} - Metrics data
 */
async function getMetricsData(js, nc, service) {
  try {
    // Default metrics as fallback
    const defaultMetrics = [
      { name: 'CPU Usage', value: 'N/A', timestamp: new Date().toISOString(), service: 'payment-service' },
      { name: 'Memory Usage', value: 'N/A', timestamp: new Date().toISOString(), service: 'payment-service' },
      { name: 'Request Rate', value: 'N/A', timestamp: new Date().toISOString(), service: 'payment-service' },
      { name: 'Error Rate', value: 'N/A', timestamp: new Date().toISOString(), service: 'payment-service' },
      { name: 'CPU Usage', value: 'N/A', timestamp: new Date().toISOString(), service: 'order-service' },
      { name: 'Memory Usage', value: 'N/A', timestamp: new Date().toISOString(), service: 'order-service' },
      { name: 'Request Rate', value: 'N/A', timestamp: new Date().toISOString(), service: 'order-service' },
      { name: 'Error Rate', value: 'N/A', timestamp: new Date().toISOString(), service: 'order-service' }
    ];

    // If no JetStream or NATS connection, return default metrics
    if (!js || !nc) {
      console.warn('NATS not available, returning default metrics with N/A values');
      return service ? defaultMetrics.filter(m => m.service === service) : defaultMetrics;
    }

    // Get JetStreamManager from the wrapper if available
    const jsm = js._jsm || null;

    if (!jsm) {
      console.warn('JetStreamManager not available, returning default metrics');
      return service ? defaultMetrics.filter(m => m.service === service) : defaultMetrics;
    }

    // Check if METRICS stream exists using JetStreamManager
    let streamExists = false;
    try {
      await jsm.streams.info(STREAM_NAMES.METRICS);
      streamExists = true;
    } catch (err) {
      console.warn(`METRICS stream not found: ${err.message}`);
      streamExists = false;
    }

    if (!streamExists) {
      // Don't try to create the stream - it should be created by the NATS server
      console.log(`${STREAM_NAMES.METRICS} stream should be created by the NATS server`);
      return service ? defaultMetrics.filter(m => m.service === service) : defaultMetrics;
    }

    // Create a consumer for the METRICS stream
    let consumer;
    try {
      consumer = await createConsumer(jsm, js, STREAM_NAMES.METRICS, CONSUMER_NAMES.METRICS);
    } catch (err) {
      console.error(`Error creating consumer for ${STREAM_NAMES.METRICS}: ${err.message}`);
      return service ? defaultMetrics.filter(m => m.service === service) : defaultMetrics;
    }

    // Fetch metric messages
    let messages = [];
    try {
      const fetchOptions = { max_messages: 100 };
      if (typeof consumer.fetch === 'function') {
        messages = await consumer.fetch(fetchOptions);
      } else if (typeof consumer.pull === 'function') {
        messages = await consumer.pull(fetchOptions.max_messages);
      } else {
        console.warn('Consumer does not support fetch or pull, using mock data');
        return service ? defaultMetrics.filter(m => m.service === service) : defaultMetrics;
      }

      // Ensure messages is iterable
      if (!messages || !Array.isArray(messages)) {
        console.warn('Messages is not an array, using default metrics');
        return service ? defaultMetrics.filter(m => m.service === service) : defaultMetrics;
      }
    } catch (err) {
      console.error(`Error fetching metrics: ${err.message}`);
      return service ? defaultMetrics.filter(m => m.service === service) : defaultMetrics;
    }

    // Process messages and collect metrics
    const metrics = [];
    const seenMetrics = new Set(); // To track unique metrics

    try {
      for (const msg of messages) {
        try {
          if (!msg || !msg.data) {
            console.warn('Invalid message format, skipping');
            continue;
          }

          const data = JSON.parse(sc.decode(msg.data));

          // Handle different data formats
          if (data.name && data.service) {
            // Original format with direct name and value
            // Create a unique key for this metric
            const metricKey = `${data.service}-${data.name}`;

            // Only add if we haven't seen this metric before (get latest value)
            if (!seenMetrics.has(metricKey)) {
              metrics.push({
                name: data.name,
                value: data.value || 'N/A',
                timestamp: data.timestamp || new Date().toISOString(),
                service: data.service
              });

              seenMetrics.add(metricKey);
            }
          } else if (data.service && data.metrics) {
            // Format with metrics object containing multiple metrics
            // Process each metric in the metrics object
            for (const [metricName, metricValue] of Object.entries(data.metrics)) {
              const metricKey = `${data.service}-${metricName}`;

              // Only add if we haven't seen this metric before (get latest value)
              if (!seenMetrics.has(metricKey)) {
                metrics.push({
                  name: metricName,
                  value: metricValue || 'N/A',
                  timestamp: data.timestamp || new Date().toISOString(),
                  service: data.service
                });

                seenMetrics.add(metricKey);
              }
            }
          }

          // Acknowledge the message
          if (typeof msg.ack === 'function') {
            await msg.ack();
          }
        } catch (err) {
          console.error(`Error processing metric message: ${err.message}`);
          // Try to acknowledge the message even if processing failed
          if (msg && typeof msg.ack === 'function') {
            await msg.ack();
          }
        }
      }
    } catch (err) {
      console.error(`Error iterating through messages: ${err.message}`);
      return service ? defaultMetrics.filter(m => m.service === service) : defaultMetrics;
    }

    // If no metrics were found, use default metrics
    if (metrics.length === 0) {
      console.warn('No metrics found in NATS, using default metrics');
      return service ? defaultMetrics.filter(m => m.service === service) : defaultMetrics;
    }

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
 * @param {object} nc - NATS connection
 * @param {string} service - Optional service filter
 * @param {string} startTime - Optional start time filter
 * @param {string} endTime - Optional end time filter
 * @returns {Promise<Array>} - Logs data
 */
async function getLogsData(js, nc, service, startTime, endTime) {
  try {
    // Default logs as fallback
    const defaultLogs = [
      { timestamp: '2023-08-15T10:30:45Z', level: 'INFO', message: 'No logs available', service: 'payment-service' },
      { timestamp: '2023-08-15T10:30:10Z', level: 'INFO', message: 'No logs available', service: 'order-service' }
    ];

    // If no JetStream or NATS connection, return default logs
    if (!js || !nc) {
      console.warn('NATS not available, returning default logs');
      let filteredLogs = defaultLogs;

      if (service) {
        filteredLogs = filteredLogs.filter(log => log.service === service);
      }

      return filteredLogs;
    }

    // Get JetStreamManager from the wrapper if available
    const jsm = js._jsm || null;

    // Check if LOGS stream exists using JetStreamManager if available
    let streamExists = false;
    try {
      if (jsm && typeof jsm.streams === 'object' && typeof jsm.streams.info === 'function') {
        // Use JetStreamManager to check for stream
        console.log('Using JetStreamManager to check for LOGS stream');
        await jsm.streams.info(STREAM_NAMES.LOGS);
        streamExists = true;
      } else {
        // Fall back to regular stream check
        streamExists = await checkStreamExists(js, STREAM_NAMES.LOGS);
      }
    } catch (err) {
      console.warn(`Stream check error: ${err.message}`);
      streamExists = false;
    }

    if (!streamExists) {
      // Don't try to create the stream - it should be created by the NATS server
      console.log(`${STREAM_NAMES.LOGS} stream should be created by the NATS server`);
    }

    if (!streamExists) {
      let filteredLogs = defaultLogs;

      if (service) {
        filteredLogs = filteredLogs.filter(log => log.service === service);
      }

      return filteredLogs;
    }

    // Create a consumer for the LOGS stream
    let consumer;
    try {
      consumer = await createConsumer(jsm, js, STREAM_NAMES.LOGS, CONSUMER_NAMES.LOGS);
    } catch (err) {
      console.error(`Error creating consumer for ${STREAM_NAMES.LOGS}: ${err.message}`);
      let filteredLogs = defaultLogs;
      if (service) {
        filteredLogs = filteredLogs.filter(log => log.service === service);
      }
      return filteredLogs;
    }

    // Fetch log messages
    let messages = [];
    try {
      const fetchOptions = { max_messages: 100 };
      if (typeof consumer.fetch === 'function') {
        messages = await consumer.fetch(fetchOptions);
      } else if (typeof consumer.pull === 'function') {
        messages = await consumer.pull(fetchOptions.max_messages);
      } else {
        console.warn('Consumer does not support fetch or pull, using mock data');
        let filteredLogs = defaultLogs;
        if (service) {
          filteredLogs = filteredLogs.filter(log => log.service === service);
        }
        return filteredLogs;
      }

      // Ensure messages is iterable
      if (!messages || !Array.isArray(messages)) {
        console.warn('Messages is not an array, using default logs');
        let filteredLogs = defaultLogs;
        if (service) {
          filteredLogs = filteredLogs.filter(log => log.service === service);
        }
        return filteredLogs;
      }
    } catch (err) {
      console.error(`Error fetching logs: ${err.message}`);
      let filteredLogs = defaultLogs;
      if (service) {
        filteredLogs = filteredLogs.filter(log => log.service === service);
      }
      return filteredLogs;
    }

    // Process messages and collect logs
    const logs = [];

    try {
      for (const msg of messages) {
        try {
          if (!msg) {
            console.warn('Invalid message: undefined or null, skipping');
            continue;
          }
          
          // Handle both the old format and our new format with _parsedData property
          let data;
          if (msg._parsedData) {
            // Use pre-parsed data from our enhanced consumer
            data = msg._parsedData;
          } else if (msg.data) {
            // Try to decode and parse the data (old approach)
            try {
              if (Buffer.isBuffer(msg.data) || msg.data instanceof Uint8Array) {
                data = JSON.parse(sc.decode(msg.data));
              } else if (typeof msg.data === 'string') {
                data = JSON.parse(msg.data);
              } else {
                // If msg.data is already an object, use it directly
                data = msg.data;
              }
            } catch (parseErr) {
              console.warn(`Log data parsing error: ${parseErr.message}. Using default log entry.`);
              data = {
                timestamp: new Date().toISOString(),
                level: 'ERROR',
                message: 'Log entry could not be parsed properly.',
                service: 'unknown-service'
              };
            }
          } else {
            console.warn('Message has no data property, skipping');
            // Acknowledge and continue
            if (typeof msg.ack === 'function') {
              await msg.ack();
            }
            continue;
          }

          if (data.message && data.service) {
            logs.push({
              timestamp: data.timestamp || new Date().toISOString(),
              level: data.level || 'INFO',
              message: data.message,
              service: data.service
            });
          }

          // Acknowledge the message
          if (typeof msg.ack === 'function') {
            await msg.ack();
          }
        } catch (err) {
          console.error(`Error processing log message: ${err.message}`);
          // Try to acknowledge the message even if processing failed
          if (msg && typeof msg.ack === 'function') {
            await msg.ack();
          }
        }
      }
    } catch (err) {
      console.error(`Error iterating through messages: ${err.message}`);
      let filteredLogs = defaultLogs;
      if (service) {
        filteredLogs = filteredLogs.filter(log => log.service === service);
      }
      return filteredLogs;
    }

    // If no logs were found, use default logs
    if (logs.length === 0) {
      console.warn('No logs found in NATS, using default logs');
      let filteredLogs = defaultLogs;

      if (service) {
        filteredLogs = filteredLogs.filter(log => log.service === service);
      }

      return filteredLogs;
    }

    // Apply filters
    let filteredLogs = logs;

    if (service) {
      filteredLogs = filteredLogs.filter(log => log.service === service);
    }

    if (startTime) {
      const startDate = new Date(startTime);
      filteredLogs = filteredLogs.filter(log => new Date(log.timestamp) >= startDate);
    }

    if (endTime) {
      const endDate = new Date(endTime);
      filteredLogs = filteredLogs.filter(log => new Date(log.timestamp) <= endDate);
    }

    // Sort logs by timestamp, most recent first
    filteredLogs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    return filteredLogs;
  } catch (error) {
    console.error('Error getting logs data:', error);
    return [];
  }
}

/**
 * Get deployment data
 * @param {object} js - JetStream instance
 * @param {object} nc - NATS connection
 * @returns {Promise<Array>} - Deployment data
 */
async function getDeploymentData(js, nc) {
  try {
    // Default deployment data as fallback
    const defaultDeployments = [
      { id: 'deploy-1', service: 'payment-service', version: 'N/A', status: 'unknown', timestamp: new Date().toISOString() },
      { id: 'deploy-2', service: 'order-service', version: 'N/A', status: 'unknown', timestamp: new Date().toISOString() },
      { id: 'deploy-3', service: 'inventory-service', version: 'N/A', status: 'unknown', timestamp: new Date().toISOString() }
    ];

    // If no JetStream or NATS connection, return default deployments
    if (!js || !nc) {
      console.warn('NATS not available, returning default deployment data');
      return defaultDeployments;
    }

    // Get JetStreamManager from the wrapper if available
    const jsm = js._jsm || null;

    // Check if DEPLOYMENTS stream exists using JetStreamManager if available
    let streamExists = false;
    try {
      if (jsm && typeof jsm.streams === 'object' && typeof jsm.streams.info === 'function') {
        // Use JetStreamManager to check for stream
        console.log('Using JetStreamManager to check for DEPLOYMENTS stream');
        await jsm.streams.info(STREAM_NAMES.DEPLOYMENTS);
        streamExists = true;
      } else {
        // Fall back to regular stream check
        streamExists = await checkStreamExists(js, STREAM_NAMES.DEPLOYMENTS);
      }
    } catch (err) {
      console.warn(`Stream check error: ${err.message}`);
      streamExists = false;
    }

    if (!streamExists) {
      // Don't try to create the stream - it should be created by the NATS server
      console.log(`${STREAM_NAMES.DEPLOYMENTS} stream should be created by the NATS server`);
    }

    if (!streamExists) {
      return defaultDeployments;
    }

    // Create a consumer for the DEPLOYMENTS stream
    let consumer;
    try {
      consumer = await createConsumer(jsm, js, STREAM_NAMES.DEPLOYMENTS, CONSUMER_NAMES.DEPLOYMENTS);
    } catch (err) {
      console.error(`Error creating consumer for ${STREAM_NAMES.DEPLOYMENTS}: ${err.message}`);
      return defaultDeployments;
    }

    // Fetch deployment messages
    let messages = [];
    try {
      const fetchOptions = { max_messages: 100 };
      if (typeof consumer.fetch === 'function') {
        messages = await consumer.fetch(fetchOptions);
      } else if (typeof consumer.pull === 'function') {
        messages = await consumer.pull(fetchOptions.max_messages);
      } else {
        console.warn('Consumer does not support fetch or pull, using mock data');
        return defaultDeployments;
      }

      // Ensure messages is iterable
      if (!messages || !Array.isArray(messages)) {
        console.warn('Messages is not an array, using default deployments');
        return defaultDeployments;
      }
    } catch (err) {
      console.error(`Error fetching deployments: ${err.message}`);
      return defaultDeployments;
    }

    // Process messages and collect deployments
    const deployments = [];
    const seenServices = new Set(); // To track unique services

    try {
      for (const msg of messages) {
        try {
          if (!msg || !msg.data) {
            console.warn('Invalid message format, skipping');
            continue;
          }

          const data = JSON.parse(sc.decode(msg.data));

          if (data.service) {
            // Only add if we haven't seen this service before (get latest deployment)
            if (!seenServices.has(data.service)) {
              deployments.push({
                id: data.id || `deploy-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
                service: data.service,
                version: data.version || 'unknown',
                status: data.status || 'unknown',
                timestamp: data.timestamp || new Date().toISOString()
              });

              seenServices.add(data.service);
            }
          }

          // Acknowledge the message
          if (typeof msg.ack === 'function') {
            await msg.ack();
          }
        } catch (err) {
          console.error(`Error processing deployment message: ${err.message}`);
          // Try to acknowledge the message even if processing failed
          if (msg && typeof msg.ack === 'function') {
            await msg.ack();
          }
        }
      }
    } catch (err) {
      console.error(`Error iterating through messages: ${err.message}`);
      return defaultDeployments;
    }

    // If no deployments were found, use default deployments
    if (deployments.length === 0) {
      console.warn('No deployments found in NATS, using default deployments');
      return defaultDeployments;
    }

    // Sort deployments by timestamp, most recent first
    deployments.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    return deployments;
  } catch (error) {
    console.error('Error getting deployment data:', error);
    return [];
  }
}

/**
 * Get root cause analysis data
 * @param {object} js - JetStream instance
 * @param {object} nc - NATS connection
 * @param {string} alertId - Optional alert ID filter
 * @returns {Promise<Array>} - Root cause analysis data
 */
async function getRootCauseData(js, nc, alertId) {
  try {
    // Default root cause data as fallback
    const defaultRootCauses = [
      {
        id: 'rc-default-1',
        alertId: 'alert-unknown',
        service: 'unknown-service',
        cause: 'No root cause analysis available',
        confidence: 0,
        timestamp: new Date().toISOString(),
        details: 'No root cause analysis data is available at this time.'
      }
    ];

    // If no JetStream, return default root causes
    if (!js || !nc) {
      console.warn('NATS not available, returning default root cause data');
      return defaultRootCauses;
    }

    // Get JetStreamManager from the wrapper if available
    const jsm = js._jsm || null;

    if (!jsm) {
      console.warn('JetStreamManager not available, returning default root cause data');
      return defaultRootCauses;
    }

    // Check if ROOT_CAUSE stream exists using JetStreamManager
    let streamExists = false;
    try {
      try {
        await jsm.streams.info(STREAM_NAMES.ROOT_CAUSES);
        streamExists = true;
        console.log(`Found ${STREAM_NAMES.ROOT_CAUSES} stream using JetStreamManager`);
      } catch (err) {
        streamExists = false;
        console.log(`${STREAM_NAMES.ROOT_CAUSES} stream should be created by the NATS server`);
      }
    } catch (err) {
      streamExists = false;
    }

    if (!streamExists) {
      return defaultRootCauses;
    }

    // Create a consumer for the ROOT_CAUSES stream
    let consumer;
    try {
      consumer = await createConsumer(jsm, js, STREAM_NAMES.ROOT_CAUSES, CONSUMER_NAMES.ROOT_CAUSES);
    } catch (err) {
      console.error(`Error creating consumer for ${STREAM_NAMES.ROOT_CAUSES}: ${err.message}`);
      return defaultRootCauses;
    }

    // Fetch root cause messages
    let messages = [];
    try {
      const fetchOptions = { max_messages: 100 };
      if (typeof consumer.fetch === 'function') {
        messages = await consumer.fetch(fetchOptions);
      } else if (typeof consumer.pull === 'function') {
        messages = await consumer.pull(fetchOptions.max_messages);
      } else {
        console.warn('Consumer does not support fetch or pull, using mock data');
        return defaultRootCauses;
      }

      // Ensure messages is iterable
      if (!messages || !Array.isArray(messages)) {
        console.warn('Messages is not an array, using default root causes');
        return defaultRootCauses;
      }
    } catch (err) {
      console.error(`Error fetching root causes: ${err.message}`);
      return defaultRootCauses;
    }

    // Process messages and collect root causes
    const rootCauses = [];

    try {
      for (const msg of messages) {
        try {
          if (!msg || !msg.data) {
            console.warn('Invalid message format, skipping');
            continue;
          }

          const data = JSON.parse(sc.decode(msg.data));

          // Handle different data formats
          if (data.service && data.cause) {
            // Original format with direct cause
            rootCauses.push({
              id: data.id || `rc-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
              alertId: data.alertId || 'unknown',
              service: data.service,
              cause: data.cause,
              confidence: data.confidence || 0.5,
              timestamp: data.timestamp || new Date().toISOString(),
              details: data.details || 'No additional details available.'
            });
          } else if (data.service && data.analysis && data.analysis.cause) {
            // Format with analysis object containing cause and other details
            rootCauses.push({
              id: data.id || `rc-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
              alertId: data.alertId || 'unknown',
              service: data.service,
              cause: data.analysis.cause,
              confidence: data.analysis.confidence || 0.5,
              timestamp: data.timestamp || new Date().toISOString(),
              details: data.analysis.recommendation || data.analysis.evidence?.join(', ') || 'No additional details available.'
            });
          }

          // Acknowledge the message
          if (typeof msg.ack === 'function') {
            await msg.ack();
          }
        } catch (err) {
          console.error(`Error processing root cause message: ${err.message}`);
          // Try to acknowledge the message even if processing failed
          if (msg && typeof msg.ack === 'function') {
            await msg.ack();
          }
        }
      }
    } catch (err) {
      console.error(`Error iterating through messages: ${err.message}`);
      return defaultRootCauses;
    }

    // If no root causes were found, use default root causes
    if (rootCauses.length === 0) {
      console.warn('No root causes found in NATS, using default root causes');
      return defaultRootCauses;
    }

    // Filter by alert ID if provided
    const filteredRootCauses = alertId ? rootCauses.filter(rc => rc.alertId === alertId) : rootCauses;

    // Sort root causes by timestamp, most recent first
    filteredRootCauses.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    return filteredRootCauses;
  } catch (error) {
    console.error('Error getting root cause data:', error);
    return [];
  }
}

/**
 * Get tracing data
 * @param {object} js - JetStream instance
 * @param {object} nc - NATS connection
 * @param {string} traceId - Optional trace ID filter
 * @param {string} service - Optional service filter
 * @returns {Promise<Array>} - Tracing data
 */
async function getTracingData(js, nc, traceId, service) {
  try {
    // Default tracing data as fallback
    const defaultTraces = [
      {
        id: 'trace-default-1',
        service: 'api-gateway',
        operation: 'No traces available',
        duration: 0,
        timestamp: new Date().toISOString(),
        spans: [
          { id: 'span-default-1', service: 'api-gateway', operation: 'No spans available', duration: 0 }
        ]
      }
    ];

    // If no JetStream, return default traces
    if (!js || !nc) {
      console.warn('NATS not available, returning default tracing data');
      return defaultTraces;
    }

    // Get JetStreamManager from the wrapper if available
    const jsm = js._jsm || null;

    // Check if TRACES stream exists using JetStreamManager if available
    let streamExists = false;
    try {
      if (jsm && typeof jsm.streams === 'object' && typeof jsm.streams.info === 'function') {
        // Use JetStreamManager to check for stream
        console.log('Using JetStreamManager to check for TRACES stream');
        await jsm.streams.info(STREAM_NAMES.TRACES);
        streamExists = true;
      } else {
        // Fall back to regular stream check
        streamExists = await checkStreamExists(js, STREAM_NAMES.TRACES);
      }
    } catch (err) {
      console.warn(`Stream check error: ${err.message}`);
      streamExists = false;
    }

    if (!streamExists) {
      // Don't try to create the stream - it should be created by the NATS server
      console.log(`${STREAM_NAMES.TRACES} stream should be created by the NATS server`);
    }

    if (!streamExists) {
      return defaultTraces;
    }

    // Create a consumer for the TRACES stream
    let consumer;
    try {
      consumer = await createConsumer(jsm, js, STREAM_NAMES.TRACES, CONSUMER_NAMES.TRACES);
    } catch (err) {
      console.error(`Error creating consumer for ${STREAM_NAMES.TRACES}: ${err.message}`);
      return defaultTraces;
    }

    // Fetch trace messages
    let messages = [];
    try {
      const fetchOptions = { max_messages: 100 };
      if (typeof consumer.fetch === 'function') {
        messages = await consumer.fetch(fetchOptions);
      } else if (typeof consumer.pull === 'function') {
        messages = await consumer.pull(fetchOptions.max_messages);
      } else {
        console.warn('Consumer does not support fetch or pull, using mock data');
        return defaultTraces;
      }

      // Ensure messages is iterable
      if (!messages || !Array.isArray(messages)) {
        console.warn('Messages is not an array, using default traces');
        return defaultTraces;
      }
    } catch (err) {
      console.error(`Error fetching traces: ${err.message}`);
      return defaultTraces;
    }

    // Process messages and collect traces
    const traces = [];

    try {
      for (const msg of messages) {
        try {
          if (!msg || !msg.data) {
            console.warn('Invalid message format, skipping');
            continue;
          }

          const data = JSON.parse(sc.decode(msg.data));

          if (data.id && data.service && data.operation) {
            traces.push({
              id: data.id,
              service: data.service,
              operation: data.operation,
              duration: data.duration || 0,
              timestamp: data.timestamp || new Date().toISOString(),
              spans: Array.isArray(data.spans) ? data.spans : []
            });
          }

          // Acknowledge the message
          if (typeof msg.ack === 'function') {
            await msg.ack();
          }
        } catch (err) {
          console.error(`Error processing trace message: ${err.message}`);
          // Try to acknowledge the message even if processing failed
          if (msg && typeof msg.ack === 'function') {
            await msg.ack();
          }
        }
      }
    } catch (err) {
      console.error(`Error iterating through messages: ${err.message}`);
      return defaultTraces;
    }

    // If no traces were found, use default traces
    if (traces.length === 0) {
      console.warn('No traces found in NATS, using default traces');
      return defaultTraces;
    }

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

    // Sort traces by timestamp, most recent first
    filteredTraces.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    return filteredTraces;
  } catch (error) {
    console.error('Error getting tracing data:', error);
    return [];
  }
}

/**
 * Get notification data
 * @param {object} js - JetStream instance
 * @param {object} nc - NATS connection
 * @returns {Promise<Array>} - Notification data
 */
async function getNotificationData(js, nc) {
  try {
    // Default notification data as fallback
    const defaultNotifications = [
      {
        id: 'notif-default-1',
        alertId: 'alert-unknown',
        channel: 'unknown',
        recipient: 'unknown',
        message: 'No notifications available',
        status: 'unknown',
        timestamp: new Date().toISOString()
      }
    ];

    // If no JetStream, return default notifications
    if (!js || !nc) {
      console.warn('NATS not available, returning default notification data');
      return defaultNotifications;
    }

    // Get JetStreamManager from the wrapper if available
    const jsm = js._jsm || null;

    if (!jsm) {
      console.warn('JetStreamManager not available, returning default notification data');
      return defaultNotifications;
    }

    // Check if NOTIFICATIONS stream exists using JetStreamManager
    let streamExists = false;
    try {
      await jsm.streams.info(STREAM_NAMES.NOTIFICATIONS);
      streamExists = true;
    } catch (err) {
      streamExists = false;
    }

    if (!streamExists) {
      // Don't try to create the stream - it should be created by the NATS server
      console.log(`${STREAM_NAMES.NOTIFICATIONS} stream should be created by the NATS server`);
    }

    if (!streamExists) {
      return defaultNotifications;
    }

    // Create a consumer for the NOTIFICATIONS stream using the utility function
    let consumer;
    try {
      consumer = await createConsumer(jsm, js, STREAM_NAMES.NOTIFICATIONS, CONSUMER_NAMES.NOTIFICATIONS);
    } catch (err) {
      console.error(`Error creating consumer for ${STREAM_NAMES.NOTIFICATIONS}: ${err.message}`);
      return defaultNotifications;
    }

    // Fetch notification messages
    let messages = [];
    try {
      const fetchOptions = { max_messages: 100 };
      if (typeof consumer.fetch === 'function') {
        messages = await consumer.fetch(fetchOptions);
      } else if (typeof consumer.pull === 'function') {
        messages = await consumer.pull(fetchOptions.max_messages);
      } else {
        throw new Error('Consumer does not support fetch or pull');
      }
    } catch (err) {
      console.error(`Error fetching notifications: ${err.message}`);
      return defaultNotifications;
    }

    // Process messages and collect notifications
    const notifications = [];

    for (const msg of messages) {
      try {
        const data = JSON.parse(sc.decode(msg.data));

        if (data.message) {
          notifications.push({
            id: data.id || `notif-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
            alertId: data.alertId || 'unknown',
            channel: data.channel || 'unknown',
            recipient: data.recipient || 'unknown',
            message: data.message,
            status: data.status || 'unknown',
            timestamp: data.timestamp || new Date().toISOString()
          });
        }

        // Acknowledge the message
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      } catch (err) {
        console.error(`Error processing notification message: ${err.message}`);
        // Try to acknowledge the message even if processing failed
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      }
    }

    // If no notifications were found, use default notifications
    if (notifications.length === 0) {
      console.warn('No notifications found in NATS, using default notifications');
      return defaultNotifications;
    }

    // Sort notifications by timestamp, most recent first
    notifications.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    return notifications;
  } catch (error) {
    console.error('Error getting notification data:', error);
    return [];
  }
}

/**
 * Get postmortem data
 * @param {object} js - JetStream instance
 * @param {object} nc - NATS connection
 * @returns {Promise<Array>} - Postmortem data
 */
async function getPostmortemData(js, nc) {
  try {
    // Default postmortem data as fallback
    const defaultPostmortems = [
      {
        id: 'pm-default-1',
        alertId: 'alert-unknown',
        title: 'No postmortems available',
        status: 'unknown',
        createdAt: new Date().toISOString(),
        summary: 'No postmortem data is available at this time.',
        impact: 'Unknown',
        rootCause: 'Unknown',
        resolution: 'Unknown',
        actionItems: ['No action items available']
      }
    ];

    // If no JetStream, return default postmortems
    if (!js || !nc) {
      console.warn('NATS not available, returning default postmortem data');
      return defaultPostmortems;
    }

    // Get JetStreamManager from the wrapper if available
    const jsm = js._jsm || null;

    if (!jsm) {
      console.warn('JetStreamManager not available, returning default postmortem data');
      return defaultPostmortems;
    }

    // Check if POSTMORTEMS stream exists using JetStreamManager
    let streamExists = false;
    try {
      await jsm.streams.info(STREAM_NAMES.POSTMORTEMS);
      streamExists = true;
    } catch (err) {
      streamExists = false;
    }

    if (!streamExists) {
      // Don't try to create the stream - it should be created by the NATS server
      console.log(`${STREAM_NAMES.POSTMORTEMS} stream should be created by the NATS server`);
    }

    if (!streamExists) {
      return defaultPostmortems;
    }

    // Create a consumer for the POSTMORTEMS stream
    let consumer;
    try {
      consumer = await createConsumer(jsm, js, STREAM_NAMES.POSTMORTEMS, CONSUMER_NAMES.POSTMORTEMS);
    } catch (err) {
      console.error(`Error creating consumer for ${STREAM_NAMES.POSTMORTEMS}: ${err.message}`);
      return defaultPostmortems;
    }

    // Fetch postmortem messages
    let messages = [];
    try {
      const fetchOptions = { max_messages: 100 };
      if (typeof consumer.fetch === 'function') {
        messages = await consumer.fetch(fetchOptions);
      } else if (typeof consumer.pull === 'function') {
        messages = await consumer.pull(fetchOptions.max_messages);
      } else {
        throw new Error('Consumer does not support fetch or pull');
      }
    } catch (err) {
      console.error(`Error fetching postmortems: ${err.message}`);
      return defaultPostmortems;
    }

    // Process messages and collect postmortems
    const postmortems = [];

    for (const msg of messages) {
      try {
        const data = JSON.parse(sc.decode(msg.data));

        if (data.title) {
          postmortems.push({
            id: data.id || `pm-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
            alertId: data.alertId || 'unknown',
            title: data.title,
            status: data.status || 'unknown',
            createdAt: data.createdAt || data.timestamp || new Date().toISOString(),
            summary: data.summary || 'No summary available',
            impact: data.impact || 'Unknown',
            rootCause: data.rootCause || 'Unknown',
            resolution: data.resolution || 'Unknown',
            actionItems: Array.isArray(data.actionItems) ? data.actionItems : ['No action items available']
          });
        }

        // Acknowledge the message
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      } catch (err) {
        console.error(`Error processing postmortem message: ${err.message}`);
        // Try to acknowledge the message even if processing failed
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      }
    }

    // If no postmortems were found, use default postmortems
    if (postmortems.length === 0) {
      console.warn('No postmortems found in NATS, using default postmortems');
      return defaultPostmortems;
    }

    // Sort postmortems by createdAt, most recent first
    postmortems.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

    return postmortems;
  } catch (error) {
    console.error('Error getting postmortem data:', error);
    return [];
  }
}

/**
 * Get runbook data
 * @param {object} js - JetStream instance
 * @param {object} nc - NATS connection
 * @param {string} runbookId - Optional runbook ID filter
 * @returns {Promise<Array>} - Runbook data
 */
async function getRunbookData(js, nc, runbookId) {
  try {
    // Default runbook data as fallback
    const defaultRunbooks = [
      {
        id: 'rb-default-1',
        title: 'No runbooks available',
        service: 'unknown-service',
        steps: ['No steps available'],
        content: '# No runbooks available\n\nPlease add runbooks using the UI or sync from an external source.',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      }
    ];

    // If no JetStream, return default runbooks
    if (!js || !nc) {
      console.warn('NATS not available, returning default runbook data');
      return runbookId ? defaultRunbooks.filter(rb => rb.id === runbookId) : defaultRunbooks;
    }

    // Get JetStreamManager from the wrapper if available
    const jsm = js._jsm || null;

    if (!jsm) {
      console.warn('JetStreamManager not available, returning default runbook data');
      return runbookId ? defaultRunbooks.filter(rb => rb.id === runbookId) : defaultRunbooks;
    }

    try {
      // Check if RUNBOOKS stream exists using JetStreamManager
      let streamExists = false;
      try {
        await jsm.streams.info(STREAM_NAMES.RUNBOOKS);
        streamExists = true;
      } catch (err) {
        streamExists = false;
      }

      if (!streamExists) {
        // Don't try to create the stream - it should be created by the NATS server
        console.log(`${STREAM_NAMES.RUNBOOKS} stream should be created by the NATS server`);
      }

      if (!streamExists) {
        return runbookId ? defaultRunbooks.filter(rb => rb.id === runbookId) : defaultRunbooks;
      }

      // Create a consumer for the RUNBOOKS stream using the new function
      let consumer;
      try {
        consumer = await createConsumer(jsm, js, STREAM_NAMES.RUNBOOKS, CONSUMER_NAMES.RUNBOOKS);
      } catch (err) {
        console.error(`Error creating consumer with createConsumer: ${err.message}`);
        return runbookId ? defaultRunbooks.filter(rb => rb.id === runbookId) : defaultRunbooks;
      }

      // Fetch runbook messages - try direct stream access if consumer methods aren't available
      let messages = [];
      try {
        const fetchOptions = { max_messages: 100 };

        if (consumer && typeof consumer.fetch === 'function') {
          console.log('Using consumer.fetch() to retrieve runbooks');
          messages = await consumer.fetch(fetchOptions);
        } else if (consumer && typeof consumer.pull === 'function') {
          console.log('Using consumer.pull() to retrieve runbooks');
          messages = await consumer.pull(fetchOptions.max_messages);
        } else {
          // Try alternative methods if consumer fetch/pull aren't available
          console.log('Consumer does not support fetch or pull, trying direct stream access');

          try {
            // Try to get all messages using the stream directly
            if (jsm && typeof jsm.streams === 'object' && typeof jsm.streams.getMessage === 'function') {
              console.log('Using JetStreamManager streams.getMessage to fetch runbooks');

              // Get stream info to find last sequence number
              const streamInfo = await jsm.streams.info(STREAM_NAMES.RUNBOOKS);
              const lastSeq = streamInfo.state?.last_seq || 0;

              if (lastSeq > 0) {
                // Fetch each message by sequence number
                for (let seq = 1; seq <= lastSeq && messages.length < 100; seq++) {
                  try {
                    const msg = await jsm.streams.getMessage(STREAM_NAMES.RUNBOOKS, { seq });
                    if (msg) {
                      messages.push(msg);
                    }
                  } catch (msgErr) {
                    console.warn(`Could not fetch message at sequence ${seq}: ${msgErr.message}`);
                    // Continue with next message if one fails
                  }
                }
              }
            } else if (typeof nc.request === 'function') {
              // Last resort: try using raw NATS API to get stream info and messages
              console.log('Using raw NATS API to fetch runbooks');

              // Get stream info
              const streamInfoResp = await nc.request(
                `$JS.API.STREAM.INFO.${STREAM_NAMES.RUNBOOKS}`,
                Buffer.from(JSON.stringify({}))
              );

              const streamInfo = JSON.parse(sc.decode(streamInfoResp.data));
              const lastSeq = streamInfo.state?.last_seq || 0;

              if (lastSeq > 0) {
                // Fetch each message by sequence number
                for (let seq = 1; seq <= lastSeq && messages.length < 100; seq++) {
                  try {
                    const msgResp = await nc.request(
                      `$JS.API.STREAM.MSG.GET.${STREAM_NAMES.RUNBOOKS}`,
                      Buffer.from(JSON.stringify({ seq }))
                    );

                    if (msgResp) {
                      const msgData = JSON.parse(sc.decode(msgResp.data));
                      // Format to match expected message structure
                      messages.push({
                        data: msgData.message,
                        subject: msgData.subject,
                        ack: async () => {} // Dummy ack function
                      });
                    }
                  } catch (msgErr) {
                    console.warn(`Could not fetch message at sequence ${seq}: ${msgErr.message}`);
                    // Continue with next message if one fails
                  }
                }
              }
            } else {
              console.warn('No suitable method found to fetch runbooks, using default data');
              return runbookId ? defaultRunbooks.filter(rb => rb.id === runbookId) : defaultRunbooks;
            }
          } catch (altErr) {
            console.error(`Error using alternative message fetching method: ${altErr.message}`);
            return runbookId ? defaultRunbooks.filter(rb => rb.id === runbookId) : defaultRunbooks;
          }
        }

        // Ensure messages is iterable
        if (!messages || !Array.isArray(messages)) {
          console.warn('Messages is not an array, using default runbooks');
          return runbookId ? defaultRunbooks.filter(rb => rb.id === runbookId) : defaultRunbooks;
        }
      } catch (err) {
        console.error(`Error fetching runbooks: ${err.message}`);
        return runbookId ? defaultRunbooks.filter(rb => rb.id === runbookId) : defaultRunbooks;
      }

      // Process messages and collect runbooks
      const runbooks = [];

      for (const msg of messages) {
        try {
          // Handle different message data formats
          let data;
          if (!msg || !msg.data) {
            console.warn('Invalid message format, skipping');
            continue;
          }

          if (typeof msg.data === 'string') {
            data = JSON.parse(msg.data);
          } else if (msg.data instanceof Uint8Array) {
            data = JSON.parse(sc.decode(msg.data));
          } else if (typeof msg.data.toString === 'function') {
            data = JSON.parse(msg.data.toString());
          } else {
            console.warn('Unrecognized message data format, skipping');
            continue;
          }

          if (data.id && data.title) {
            runbooks.push({
              id: data.id,
              title: data.title,
              service: data.service || 'unknown-service',
              steps: Array.isArray(data.steps) ? data.steps : [],
              content: data.content || '',
              createdAt: data.createdAt || new Date().toISOString(),
              updatedAt: data.updatedAt || new Date().toISOString()
            });
          }

          // Acknowledge the message if possible
          if (typeof msg.ack === 'function') {
            await msg.ack();
          }
        } catch (err) {
          console.error(`Error processing runbook message: ${err.message}`);
          // Try to acknowledge the message even if processing failed
          if (typeof msg.ack === 'function') {
            await msg.ack();
          }
        }
      }

      // If no runbooks were found, use default runbooks
      if (runbooks.length === 0) {
        console.warn('No runbooks found in NATS, using default runbooks');
        return runbookId ? defaultRunbooks.filter(rb => rb.id === runbookId) : defaultRunbooks;
      }

      // Filter by runbook ID if provided
      const filteredRunbooks = runbookId ? runbooks.filter(rb => rb.id === runbookId) : runbooks;

      // Sort runbooks by updatedAt, most recent first
      filteredRunbooks.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));

      return filteredRunbooks;
    } catch (err) {
      console.warn(`Error fetching runbooks: ${err.message}`);
      console.error('Error details:', err);
      return runbookId ? defaultRunbooks.filter(rb => rb.id === runbookId) : defaultRunbooks;
    }
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
    // Check if JetStream is available
    if (!js) {
      throw new Error('NATS JetStream is required for runbook execution. Please ensure NATS is properly configured and running.');
    }

    // Get the NATS connection from the JetStream wrapper
    const nc = js._nc || null;
    if (!nc) {
      throw new Error('NATS connection is required for runbook execution. Please ensure NATS is properly configured and running.');
    }

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

    // Prepare execution request
    const executionRequest = {
      executionId,
      runbookId,
      runbook,
      timestamp: new Date().toISOString()
    };

    // Try to send execution request to runbook agent via JetStream
    try {
      // Use our wrapper to publish
      await js.publish('runbook.execute', sc.encode(JSON.stringify(executionRequest)));
      console.log(`Published runbook execution request to runbook.execute: ${executionId}`);
    } catch (pubErr) {
      console.warn(`Error publishing with JetStream: ${pubErr.message}. Trying regular NATS publish.`);

      // Fallback to regular NATS publish
      if (typeof nc.publish === 'function') {
        nc.publish('runbook.execute', sc.encode(JSON.stringify(executionRequest)));
        console.log(`Published runbook execution request using regular NATS: ${executionId}`);
      } else {
        throw new Error('Failed to publish runbook execution request. Neither JetStream nor regular NATS publish is working.');
      }
    }

    // Set up a subscription to receive execution updates
    setupExecutionSubscription(executionId, nc);

    return {
      executionId,
      runbookId,
      status: 'starting',
      message: 'Runbook execution started',
      mode: 'real'
    };
  } catch (error) {
    console.error('Error executing runbook:', error);
    throw error;
  }
}

/**
 * Set up a subscription to receive execution updates
 * @param {string} executionId - ID of the execution to track
 * @param {object} nc - NATS connection
 */
function setupExecutionSubscription(executionId, nc) {
  if (!nc) {
    console.warn(`Cannot set up subscription for ${executionId}: NATS connection not available`);
    return;
  }

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
      // First check if stream exists using our helper
      const streamExists = await checkStreamExists(js, 'RUNBOOKS');

      if (!streamExists) {
        // Try to create the stream using the appropriate API
        if (js._jsm && typeof js._jsm.streams === 'object' && typeof js._jsm.streams.add === 'function') {
          console.log('Using JetStream Manager to create RUNBOOKS stream');
          await js._jsm.streams.add({
            name: 'RUNBOOKS',
            subjects: ['runbooks.*']
          });
        } else if (typeof js.streams === 'object' && typeof js.streams.add === 'function') {
          console.log('Using newer JetStream API to create RUNBOOKS stream');
          await js.streams.add({
            name: 'RUNBOOKS',
            subjects: ['runbooks.*']
          });
        } else if (typeof js.addStream === 'function') {
          console.log('Using older JetStream API to create RUNBOOKS stream');
          await js.addStream({
            name: 'RUNBOOKS',
            subjects: ['runbooks.*']
          });
        } else {
          throw new Error('No suitable JetStream API available to create stream');
        }
      }

      // Ensure consumer exists
      try {
        if (js._jsm && typeof js._jsm.consumers === 'object' && typeof js._jsm.consumers.info === 'function') {
          await js._jsm.consumers.info('RUNBOOKS', 'runbook-viewer').catch(async () => {
            console.log('Using JetStream Manager to create runbook-viewer consumer');
            return js._jsm.consumers.add('RUNBOOKS', {
              durable_name: 'runbook-viewer',
              ack_policy: 'explicit',
              deliver_policy: 'all'
            });
          });
        } else if (typeof js.consumers === 'object' && typeof js.consumers.info === 'function') {
          await js.consumers.info('RUNBOOKS', 'runbook-viewer').catch(async () => {
            console.log('Using newer JetStream API to create runbook-viewer consumer');
            return js.consumers.add('RUNBOOKS', {
              durable_name: 'runbook-viewer',
              ack_policy: 'explicit',
              deliver_policy: 'all'
            });
          });
        } else {
          // Use the wrapper's getConsumer method which handles different API versions
          await js.getConsumer('RUNBOOKS', 'runbook-viewer');
        }
      } catch (consumerErr) {
        console.warn(`Error ensuring consumer exists: ${consumerErr.message}`);
        // Continue anyway, as we might still be able to publish
      }
    } catch (err) {
      console.error('Error setting up RUNBOOKS stream:', err);
      throw new Error('Failed to set up RUNBOOKS stream');
    }

    // Publish runbook to JetStream
    if (js._jsm && typeof js._jsm.streams === 'object' && typeof js._jsm.streams.info === 'function') {
      console.log('Using JetStreamManager to publish runbook');
      await js._jsm.streams.info('RUNBOOKS').catch(async () => {
        console.log('Creating RUNBOOKS stream with JetStreamManager');
        await js._jsm.streams.add({
          name: 'RUNBOOKS',
          subjects: ['runbooks.*']
        });
      });
      await js.publish(`runbooks.${runbook.id}`, JSON.stringify(runbook));
    } else {
      // Fallback to direct publish without checking stream
      console.warn('JetStreamManager not available, attempting direct publish');
      await js.publish(`runbooks.${runbook.id}`, JSON.stringify(runbook));
    }

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

      if (!syncData.path) {
        syncData.path = 'runbooks'; // Default path if not specified
      }

      // Ensure RUNBOOKS stream exists
      let streamExists = false;

      // Get JetStreamManager from the wrapper if available
      const jsm = js._jsm || null;

      try {
        if (jsm && typeof jsm.streams === 'object' && typeof jsm.streams.info === 'function') {
          // Use JetStreamManager to check for stream
          console.log(`Using JetStreamManager to check for ${STREAM_NAMES.RUNBOOKS} stream`);
          try {
            await jsm.streams.info(STREAM_NAMES.RUNBOOKS);
            streamExists = true;
          } catch (streamErr) {
            streamExists = false;
          }
        } else {
          // Fall back to regular stream check
          streamExists = await checkStreamExists(js, STREAM_NAMES.RUNBOOKS);
        }
      } catch (checkErr) {
        console.warn(`Stream check error: ${checkErr.message}`);
        streamExists = false;
      }

      if (!streamExists) {
        // Create stream if it doesn't exist
        try {
          if (jsm && typeof jsm.streams === 'object' && typeof jsm.streams.add === 'function') {
            // Use JetStreamManager to create stream
            console.log(`Using JetStreamManager to create ${STREAM_NAMES.RUNBOOKS} stream`);
            await jsm.streams.add({
              name: STREAM_NAMES.RUNBOOKS,
              subjects: ['runbooks.*']
            });
          } else if (typeof js.streams === 'object' && typeof js.streams.add === 'function') {
            // Use newer JetStream API
            console.log(`Using newer JetStream API to create ${STREAM_NAMES.RUNBOOKS} stream`);
            await js.streams.add({
              name: STREAM_NAMES.RUNBOOKS,
              subjects: ['runbooks.*']
            });
          } else if (typeof js.addStream === 'function') {
            // Fall back to older JetStream API as last resort
            console.log(`Using older JetStream API to create ${STREAM_NAMES.RUNBOOKS} stream`);
            await js.addStream({
              name: STREAM_NAMES.RUNBOOKS,
              subjects: ['runbooks.*']
            });
          } else {
            throw new Error('No suitable JetStream API available to create stream');
          }
          console.log(`Created ${STREAM_NAMES.RUNBOOKS} stream`);
        } catch (err) {
          console.error(`Error creating ${STREAM_NAMES.RUNBOOKS} stream: ${err.message}`);
          throw new Error(`Failed to create ${STREAM_NAMES.RUNBOOKS} stream`);
        }
      }

      // Fetch runbooks from GitHub
      console.log(`Fetching runbooks from GitHub repository: ${syncData.repo}, path: ${syncData.path}`);

      try {
        // Parse the repo into owner and repo name
        const [owner, repo] = syncData.repo.split('/');
        if (!owner || !repo) {
          throw new Error('Invalid GitHub repository format. Expected format: owner/repo');
        }

        // Construct the GitHub API URL to get contents of the specified path
        const apiUrl = `https://api.github.com/repos/${owner}/${repo}/contents/${syncData.path}`;
        console.log(`Fetching from GitHub API: ${apiUrl}`);

        // Make the request to GitHub API
        const response = await axios.get(apiUrl, {
          headers: {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Observability-Agent-UI'
          }
        });

        if (!response.data || !Array.isArray(response.data)) {
          throw new Error('Invalid response from GitHub API');
        }

        // Filter for markdown files
        const mdFiles = response.data.filter(file =>
          file.type === 'file' && (file.name.endsWith('.md') || file.name.endsWith('.markdown'))
        );

        if (mdFiles.length === 0) {
          throw new Error(`No markdown files found in ${syncData.path}`);
        }

        console.log(`Found ${mdFiles.length} markdown files`);

        // Fetch and process each markdown file
        const runbooks = [];

        for (const file of mdFiles) {
          // Get the file content
          const contentResponse = await axios.get(file.download_url);
          const content = contentResponse.data;

          // Extract title from the first heading or use filename
          let title = file.name.replace(/\.md$|\.markdown$/i, '');
          const titleMatch = content.match(/^#\s+(.+)$/m);
          if (titleMatch && titleMatch[1]) {
            title = titleMatch[1].trim();
          }

          // Extract service from frontmatter or path
          let service = 'unknown-service';
          const serviceFrontmatter = content.match(/^---[\s\S]*?service:\s*([^\s\n]+)[\s\S]*?---/m);
          if (serviceFrontmatter && serviceFrontmatter[1]) {
            service = serviceFrontmatter[1].trim();
          }

          // Create a unique ID for the runbook
          const id = `rb-github-${Date.now()}-${runbooks.length + 1}`;

          // Parse steps from the content
          const steps = parseRunbookSteps(content);

          // Create the runbook object
          const runbook = {
            id,
            title,
            service,
            steps,
            content,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            source: `github:${syncData.repo}/${file.path}`
          };

          // Publish the runbook to JetStream
          await js.publish(`runbooks.${runbook.id}`, sc.encode(JSON.stringify(runbook)));

          runbooks.push(runbook);
        }

        return { success: true, count: runbooks.length };
      } catch (apiErr) {
        console.error('GitHub API error:', apiErr);

        // If we can't access GitHub API, create some sample runbooks as fallback
        console.warn('Falling back to sample runbooks due to GitHub API error');

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
            source: `github:${syncData.repo} (sample)`
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
            source: `github:${syncData.repo} (sample)`
          }
        ];

        // Publish sample runbooks to JetStream
        for (const runbook of runbooks) {
          await js.publish(`runbooks.${runbook.id}`, sc.encode(JSON.stringify(runbook)));
        }

        return {
          success: true,
          count: runbooks.length,
          warning: `Used sample runbooks due to GitHub API error: ${apiErr.message}`
        };
      }
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

// Create Express application
const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(bodyParser.json());

// Health check endpoint
app.get('/health', (_, res) => {
  res.status(200).json({ status: 'ok' });
});

// NATS connection and JetStream instance
let nc = null;
let js = null;

// Connect to NATS
async function connectToNATS() {
  try {
    console.log(`Connecting to NATS at ${NATS_URL}...`);
    nc = await connect({ servers: NATS_URL });
    console.log(`Connected to NATS at ${NATS_URL}`);

    // Create JetStream instance
    js = nc.jetstream();
    console.log('JetStream client created');

    // Get JetStreamManager if available
    try {
      js._jsm = await nc.jetstreamManager();
      console.log('JetStreamManager available');
    } catch (err) {
      console.warn(`JetStreamManager not available: ${err.message}`);
      js._jsm = null;
    }

    // Store NATS connection in JetStream for convenience
    js._nc = nc;

    return { nc, js };
  } catch (error) {
    console.error(`Error connecting to NATS: ${error.message}`);
    // Create mock JetStream client for fallback
    console.warn('Using mock JetStream client');
    js = createMockJetStream();
    return { nc: null, js };
  }
}

// Create a mock JetStream client for fallback
function createMockJetStream() {
  console.warn('Creating mock JetStream client');
  return {
    _nc: null,
    _jsm: null,
    publish: async (subject, _) => {
      console.log(`Mock publish to ${subject}`);
      return { seq: Math.floor(Math.random() * 1000) };
    },
    consumers: {
      get: async () => {
        console.warn('JetStream API does not support getting consumers, using fallback');
        throw new Error('Not implemented in mock');
      }
    },
    // Add other methods as needed
    getConsumer: async () => {
      console.warn('Using mock consumer fetch');
      return {
        fetch: async () => []
      };
    }
  };
}

// API Routes

// Get all agents
app.get('/api/agents', async (req, res) => {
  try {
    const agents = await getData('agents', js, nc, req);
    res.json(agents);
  } catch (error) {
    console.error('Error fetching agents:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get metrics data
app.get('/api/metrics', async (req, res) => {
  try {
    const metrics = await getData('metrics', js, nc, req);
    res.json(metrics);
  } catch (error) {
    console.error('Error fetching metrics:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get logs data
app.get('/api/logs', async (req, res) => {
  try {
    const logs = await getData('logs', js, nc, req);
    res.json(logs);
  } catch (error) {
    console.error('Error fetching logs:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get deployment data
app.get('/api/deployment', async (req, res) => {
  try {
    const deployments = await getData('deployment', js, nc, req);
    res.json(deployments);
  } catch (error) {
    console.error('Error fetching deployments:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get root cause analysis data
app.get('/api/rootcause', async (req, res) => {
  try {
    const rootCauses = await getData('rootcause', js, nc, req);
    res.json(rootCauses);
  } catch (error) {
    console.error('Error fetching root causes:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get tracing data
app.get('/api/tracing', async (req, res) => {
  try {
    const traces = await getData('tracing', js, nc, req);
    res.json(traces);
  } catch (error) {
    console.error('Error fetching traces:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get notification data
app.get('/api/notification', async (req, res) => {
  try {
    const notifications = await getData('notification', js, nc, req);
    res.json(notifications);
  } catch (error) {
    console.error('Error fetching notifications:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get postmortem data
app.get('/api/postmortem', async (req, res) => {
  try {
    const postmortems = await getData('postmortem', js, nc, req);
    res.json(postmortems);
  } catch (error) {
    console.error('Error fetching postmortems:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get runbook data
app.get('/api/runbook', async (req, res) => {
  try {
    const runbooks = await getData('runbook', js, nc, req);
    res.json(runbooks);
  } catch (error) {
    console.error('Error fetching runbooks:', error);
    res.status(500).json({ error: error.message });
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
    res.status(500).json({ error: error.message });
  }
});

// Get runbook execution status
app.get('/api/runbook/execution/:executionId', (req, res) => {
  try {
    const { executionId } = req.params;
    if (!executionId) {
      return res.status(400).json({ error: 'Execution ID is required' });
    }

    const status = getRunbookExecutionStatus(executionId);
    res.json(status);
  } catch (error) {
    console.error('Error getting execution status:', error);
    res.status(500).json({ error: error.message });
  }
});

// Add a new runbook
app.post('/api/runbook', async (req, res) => {
  try {
    const result = await addRunbook(js, req.body);
    res.json(result);
  } catch (error) {
    console.error('Error adding runbook:', error);
    res.status(500).json({ error: error.message });
  }
});

// Sync runbooks from external source
app.post('/api/runbook/sync', async (req, res) => {
  try {
    const result = await syncRunbooks(js, req.body);
    res.json(result);
  } catch (error) {
    console.error('Error syncing runbooks:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get historical alerts
app.get('/api/alerts/history', async (req, res) => {
  try {
    const alerts = await getData('alerts/history', js, nc, req);
    res.json(alerts);
  } catch (error) {
    console.error('Error fetching historical alerts:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get active alerts
app.get('/api/alerts/active', async (req, res) => {
  try {
    const alerts = await getData('alerts/active', js, nc, req);
    res.json(alerts);
  } catch (error) {
    console.error('Error fetching active alerts:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get incidents from knowledge base
app.get('/api/knowledge/incidents', async (req, res) => {
  try {
    const incidents = await getData('knowledge/incidents', js, nc, req);
    res.json(incidents);
  } catch (error) {
    console.error('Error fetching incidents:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get postmortems from knowledge base
app.get('/api/knowledge/postmortems', async (req, res) => {
  try {
    const postmortems = await getData('knowledge/postmortems', js, nc, req);
    res.json(postmortems);
  } catch (error) {
    console.error('Error fetching postmortems:', error);
    res.status(500).json({ error: error.message });
  }
});

// Start the server
async function startServer() {
  // Connect to NATS
  await connectToNATS();

  // Start Express server
  app.listen(PORT, () => {
    console.log(`UI Backend listening on port ${PORT}`);
  });
}

// Start the server
startServer().catch(err => {
  console.error('Failed to start server:', err);
});