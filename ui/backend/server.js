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
const NATS_DOMAIN = process.env.NATS_DOMAIN || 'observability-agent';
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

    // Check if AGENTS stream exists
    let streamExists = false;
    try {
      await js.streamInfo('AGENTS');
      streamExists = true;
    } catch (err) {
      console.warn(`AGENTS stream not found: ${err.message}`);
      // Try to create the stream
      try {
        await js.addStream({
          name: 'AGENTS',
          subjects: ['agent.status.*']
        });
        streamExists = true;
        console.log('Created AGENTS stream');
      } catch (createErr) {
        console.error(`Error creating AGENTS stream: ${createErr.message}`);
      }
    }

    if (!streamExists) {
      return defaultAgents;
    }

    // Create a consumer for the AGENTS stream
    let consumer;
    try {
      consumer = await js.getConsumer('AGENTS', 'agent-status-viewer').catch(async () => {
        // Create consumer if it doesn't exist
        return await js.addConsumer('AGENTS', {
          durable_name: 'agent-status-viewer',
          ack_policy: 'explicit',
          deliver_policy: 'all'
        });
      });
    } catch (err) {
      console.error(`Error creating consumer: ${err.message}`);
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

    // Check if METRICS stream exists
    let streamExists = false;
    try {
      await js.streamInfo('METRICS');
      streamExists = true;
    } catch (err) {
      console.warn(`METRICS stream not found: ${err.message}`);
      // Don't try to create the stream - it should be created by the NATS server
      console.log('METRICS stream should be created by the NATS server');
    }

    if (!streamExists) {
      return service ? defaultMetrics.filter(m => m.service === service) : defaultMetrics;
    }

    // Create a consumer for the METRICS stream
    let consumer;
    try {
      consumer = await js.getConsumer('METRICS', 'metrics-viewer').catch(async () => {
        // Create consumer if it doesn't exist
        return await js.addConsumer('METRICS', {
          durable_name: 'metrics-viewer',
          ack_policy: 'explicit',
          deliver_policy: 'all'
        });
      });
    } catch (err) {
      console.error(`Error creating consumer: ${err.message}`);
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
        throw new Error('Consumer does not support fetch or pull');
      }
    } catch (err) {
      console.error(`Error fetching metrics: ${err.message}`);
      return service ? defaultMetrics.filter(m => m.service === service) : defaultMetrics;
    }

    // Process messages and collect metrics
    const metrics = [];
    const seenMetrics = new Set(); // To track unique metrics

    for (const msg of messages) {
      try {
        const data = JSON.parse(sc.decode(msg.data));

        if (data.name && data.service) {
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
        }

        // Acknowledge the message
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      } catch (err) {
        console.error(`Error processing metric message: ${err.message}`);
        // Try to acknowledge the message even if processing failed
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      }
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

    // Check if LOGS stream exists
    let streamExists = false;
    try {
      await js.streamInfo('LOGS');
      streamExists = true;
    } catch (err) {
      console.warn(`LOGS stream not found: ${err.message}`);
      // Don't try to create the stream - it should be created by the NATS server
      console.log('LOGS stream should be created by the NATS server');
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
      consumer = await js.getConsumer('LOGS', 'logs-viewer').catch(async () => {
        // Create consumer if it doesn't exist
        return await js.addConsumer('LOGS', {
          durable_name: 'logs-viewer',
          ack_policy: 'explicit',
          deliver_policy: 'all'
        });
      });
    } catch (err) {
      console.error(`Error creating consumer: ${err.message}`);
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
        throw new Error('Consumer does not support fetch or pull');
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

    for (const msg of messages) {
      try {
        const data = JSON.parse(sc.decode(msg.data));

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
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      }
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

    // Check if DEPLOYMENTS stream exists
    let streamExists = false;
    try {
      await js.streamInfo('DEPLOYMENTS');
      streamExists = true;
    } catch (err) {
      console.warn(`DEPLOYMENTS stream not found: ${err.message}`);
      // Don't try to create the stream - it should be created by the NATS server
      console.log('DEPLOYMENTS stream should be created by the NATS server');
    }

    if (!streamExists) {
      return defaultDeployments;
    }

    // Create a consumer for the DEPLOYMENTS stream
    let consumer;
    try {
      consumer = await js.getConsumer('DEPLOYMENTS', 'deployment-viewer').catch(async () => {
        // Create consumer if it doesn't exist
        return await js.addConsumer('DEPLOYMENTS', {
          durable_name: 'deployment-viewer',
          ack_policy: 'explicit',
          deliver_policy: 'all'
        });
      });
    } catch (err) {
      console.error(`Error creating consumer: ${err.message}`);
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
        throw new Error('Consumer does not support fetch or pull');
      }
    } catch (err) {
      console.error(`Error fetching deployments: ${err.message}`);
      return defaultDeployments;
    }

    // Process messages and collect deployments
    const deployments = [];
    const seenServices = new Set(); // To track unique services

    for (const msg of messages) {
      try {
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
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      }
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

    // Check if ROOT_CAUSE stream exists
    let streamExists = false;
    try {
      await js.streamInfo('ROOT_CAUSE');
      streamExists = true;
    } catch (err) {
      console.warn(`ROOT_CAUSE stream not found: ${err.message}`);
      // Don't try to create the stream - it should be created by the NATS server
      console.log('ROOT_CAUSE stream should be created by the NATS server');
    }

    if (!streamExists) {
      return defaultRootCauses;
    }

    // Create a consumer for the ROOTCAUSES stream
    let consumer;
    try {
      consumer = await js.getConsumer('ROOTCAUSES', 'rootcause-viewer').catch(async () => {
        // Create consumer if it doesn't exist
        return await js.addConsumer('ROOTCAUSES', {
          durable_name: 'rootcause-viewer',
          ack_policy: 'explicit',
          deliver_policy: 'all'
        });
      });
    } catch (err) {
      console.error(`Error creating consumer: ${err.message}`);
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
        throw new Error('Consumer does not support fetch or pull');
      }
    } catch (err) {
      console.error(`Error fetching root causes: ${err.message}`);
      return defaultRootCauses;
    }

    // Process messages and collect root causes
    const rootCauses = [];

    for (const msg of messages) {
      try {
        const data = JSON.parse(sc.decode(msg.data));

        if (data.service && data.cause) {
          rootCauses.push({
            id: data.id || `rc-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
            alertId: data.alertId || 'unknown',
            service: data.service,
            cause: data.cause,
            confidence: data.confidence || 0.5,
            timestamp: data.timestamp || new Date().toISOString(),
            details: data.details || 'No additional details available.'
          });
        }

        // Acknowledge the message
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      } catch (err) {
        console.error(`Error processing root cause message: ${err.message}`);
        // Try to acknowledge the message even if processing failed
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      }
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

    // Check if TRACES stream exists
    let streamExists = false;
    try {
      await js.streamInfo('TRACES');
      streamExists = true;
    } catch (err) {
      console.warn(`TRACES stream not found: ${err.message}`);
      // Don't try to create the stream - it should be created by the NATS server
      console.log('TRACES stream should be created by the NATS server');
    }

    if (!streamExists) {
      return defaultTraces;
    }

    // Create a consumer for the TRACES stream
    let consumer;
    try {
      consumer = await js.getConsumer('TRACES', 'trace-viewer').catch(async () => {
        // Create consumer if it doesn't exist
        return await js.addConsumer('TRACES', {
          durable_name: 'trace-viewer',
          ack_policy: 'explicit',
          deliver_policy: 'all'
        });
      });
    } catch (err) {
      console.error(`Error creating consumer: ${err.message}`);
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
        throw new Error('Consumer does not support fetch or pull');
      }
    } catch (err) {
      console.error(`Error fetching traces: ${err.message}`);
      return defaultTraces;
    }

    // Process messages and collect traces
    const traces = [];

    for (const msg of messages) {
      try {
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
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      }
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

    // Check if NOTIFICATIONS stream exists
    let streamExists = false;
    try {
      await js.streamInfo('NOTIFICATIONS');
      streamExists = true;
    } catch (err) {
      console.warn(`NOTIFICATIONS stream not found: ${err.message}`);
      // Don't try to create the stream - it should be created by the NATS server
      console.log('NOTIFICATIONS stream should be created by the NATS server');
    }

    if (!streamExists) {
      return defaultNotifications;
    }

    // Create a consumer for the NOTIFICATIONS stream
    let consumer;
    try {
      consumer = await js.getConsumer('NOTIFICATIONS', 'notification-viewer').catch(async () => {
        // Create consumer if it doesn't exist
        return await js.addConsumer('NOTIFICATIONS', {
          durable_name: 'notification-viewer',
          ack_policy: 'explicit',
          deliver_policy: 'all'
        });
      });
    } catch (err) {
      console.error(`Error creating consumer: ${err.message}`);
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

    // Check if POSTMORTEMS stream exists
    let streamExists = false;
    try {
      await js.streamInfo('POSTMORTEMS');
      streamExists = true;
    } catch (err) {
      console.warn(`POSTMORTEMS stream not found: ${err.message}`);
      // Don't try to create the stream - it should be created by the NATS server
      console.log('POSTMORTEMS stream should be created by the NATS server');
    }

    if (!streamExists) {
      return defaultPostmortems;
    }

    // Create a consumer for the POSTMORTEMS stream
    let consumer;
    try {
      consumer = await js.getConsumer('POSTMORTEMS', 'postmortem-viewer').catch(async () => {
        // Create consumer if it doesn't exist
        return await js.addConsumer('POSTMORTEMS', {
          durable_name: 'postmortem-viewer',
          ack_policy: 'explicit',
          deliver_policy: 'all'
        });
      });
    } catch (err) {
      console.error(`Error creating consumer: ${err.message}`);
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

    try {
      // Check if RUNBOOKS stream exists
      let streamExists = false;
      try {
        await js.streamInfo('RUNBOOKS');
        streamExists = true;
      } catch (err) {
        console.warn(`RUNBOOKS stream not found: ${err.message}`);
        // Don't try to create the stream - it should be created by the NATS server
        console.log('RUNBOOKS stream should be created by the NATS server');
      }

      if (!streamExists) {
        return runbookId ? defaultRunbooks.filter(rb => rb.id === runbookId) : defaultRunbooks;
      }

      // Create a consumer for the RUNBOOKS stream
      let consumer;
      try {
        consumer = await js.getConsumer('RUNBOOKS', 'runbook-viewer').catch(async () => {
          // Create consumer if it doesn't exist
          return await js.addConsumer('RUNBOOKS', {
            durable_name: 'runbook-viewer',
            ack_policy: 'explicit',
            deliver_policy: 'all'
          });
        });
      } catch (err) {
        console.error(`Error creating consumer: ${err.message}`);
        return runbookId ? defaultRunbooks.filter(rb => rb.id === runbookId) : defaultRunbooks;
      }

      // Fetch runbook messages
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
        console.error(`Error fetching runbooks: ${err.message}`);
        return runbookId ? defaultRunbooks.filter(rb => rb.id === runbookId) : defaultRunbooks;
      }

      // Process messages and collect runbooks
      const runbooks = [];

      for (const msg of messages) {
        try {
          // Handle different message data formats
          let data;
          if (typeof msg.data === 'string') {
            data = JSON.parse(msg.data);
          } else if (msg.data instanceof Uint8Array) {
            data = JSON.parse(sc.decode(msg.data));
          } else {
            data = JSON.parse(msg.data.toString());
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

          // Acknowledge the message
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
    // Check if NATS and JetStream are available
    if (!js || !nc) {
      throw new Error('NATS JetStream is required for runbook execution. Please ensure NATS is properly configured and running.');
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
    setupExecutionSubscription(executionId);

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

      if (!syncData.path) {
        syncData.path = 'runbooks'; // Default path if not specified
      }

      // Ensure RUNBOOKS stream exists
      try {
        await js.streamInfo('RUNBOOKS');
      } catch (err) {
        // Create stream if it doesn't exist
        await js.addStream({
          name: 'RUNBOOKS',
          subjects: ['runbooks.*']
        });
        console.log('Created RUNBOOKS stream');
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
      debug: process.env.DEBUG === 'true',
      jetstreamDomain: NATS_DOMAIN
    });

    nc = await connect({
      servers: NATS_URL,
      timeout: 5000,
      debug: process.env.DEBUG === 'true'
      // Removed JetStream domain to use default domain
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
              _originalJs: js, // Keep a reference to the original JetStream object
              _nc: nc, // Keep a reference to the NATS connection
              _domain: NATS_DOMAIN, // Store the domain

              // Method to get stream info
              async streamInfo(streamName) {
                try {
                  if (typeof this._js.streams === 'object' && typeof this._js.streams.info === 'function') {
                    console.log('Using newer JetStream API (streams.info)');
                    return this._js.streams.info(streamName);
                  } else if (typeof this._js.streamInfo === 'function') {
                    console.log('Using older JetStream API (streamInfo)');
                    return this._js.streamInfo(streamName);
                  } else {
                    console.warn('JetStream API does not support stream info, returning mock info');
                    // Return a mock stream info to avoid errors
                    return {
                      name: streamName,
                      subjects: [`${streamName.toLowerCase()}.*`],
                      config: {
                        name: streamName,
                        subjects: [`${streamName.toLowerCase()}.*`],
                        retention: 'limits',
                        max_consumers: -1,
                        max_msgs: -1,
                        max_bytes: -1,
                        max_age: 0,
                        max_msg_size: -1,
                        storage: 'file',
                        discard: 'old',
                        num_replicas: 1
                      },
                      created: new Date().toISOString()
                    };
                  }
                } catch (error) {
                  console.error(`Error in streamInfo for ${streamName}:`, error);
                  throw error;
                }
              },

              // Method to add a stream
              async addStream(config) {
                try {
                  if (typeof this._js.streams === 'object' && typeof this._js.streams.add === 'function') {
                    console.log('Using newer JetStream API (streams.add)');
                    return this._js.streams.add(config);
                  } else if (typeof this._js.addStream === 'function') {
                    console.log('Using older JetStream API (addStream)');
                    return this._js.addStream(config);
                  } else {
                    console.warn('JetStream API does not support adding streams, using fallback');
                    // Return a mock stream info to avoid errors
                    return {
                      name: config.name,
                      subjects: config.subjects,
                      config: {
                        ...config,
                        retention: 'limits',
                        max_consumers: -1,
                        max_msgs: -1,
                        max_bytes: -1,
                        max_age: 0,
                        max_msg_size: -1,
                        storage: 'file',
                        discard: 'old',
                        num_replicas: 1
                      },
                      created: new Date().toISOString()
                    };
                  }
                } catch (error) {
                  console.error(`Error in addStream for ${config.name}:`, error);
                  // Return a mock stream info to avoid errors
                  return {
                    name: config.name,
                    subjects: config.subjects,
                    config: {
                      ...config,
                      retention: 'limits',
                      max_consumers: -1,
                      max_msgs: -1,
                      max_bytes: -1,
                      max_age: 0,
                      max_msg_size: -1,
                      storage: 'file',
                      discard: 'old',
                      num_replicas: 1
                    },
                    created: new Date().toISOString()
                  };
                }
              },

              // Method to get a consumer
              async getConsumer(streamName, consumerName) {
                try {
                  if (typeof this._js.consumers === 'object' && typeof this._js.consumers.get === 'function') {
                    console.log('Using newer JetStream API (consumers.get)');
                    return this._js.consumers.get(streamName, consumerName);
                  } else if (typeof this._js.consumer === 'function') {
                    console.log('Using older JetStream API (consumer)');
                    // @ts-ignore - Support for older JetStream API versions
                    return this._js.consumer(streamName, { durable_name: consumerName });
                  } else if (typeof this._js.consumers === 'function') {
                    console.log('Using alternative JetStream API (consumers)');
                    return this._js.consumers(streamName, { durable_name: consumerName });
                  } else {
                    console.warn('JetStream API does not support getting consumers, using fallback');
                    // Return a mock consumer to avoid errors
                    return {
                      name: consumerName,
                      stream_name: streamName,
                      config: {
                        durable_name: consumerName,
                        ack_policy: 'explicit',
                        deliver_policy: 'all'
                      },
                      created: new Date().toISOString(),
                      // Mock fetch method
                      fetch: async () => {
                        console.log('Using mock consumer fetch');
                        return [];
                      },
                      // Mock pull method
                      pull: async () => {
                        console.log('Using mock consumer pull');
                        return [];
                      }
                    };
                  }
                } catch (error) {
                  console.error(`Error in getConsumer for ${streamName}/${consumerName}:`, error);
                  // Return a mock consumer to avoid errors
                  return {
                    name: consumerName,
                    stream_name: streamName,
                    config: {
                      durable_name: consumerName,
                      ack_policy: 'explicit',
                      deliver_policy: 'all'
                    },
                    created: new Date().toISOString(),
                    // Mock fetch method
                    fetch: async () => {
                      console.log('Using mock consumer fetch');
                      return [];
                    },
                    // Mock pull method
                    pull: async () => {
                      console.log('Using mock consumer pull');
                      return [];
                    }
                  };
                }
              },

              // Method to add a consumer
              async addConsumer(streamName, config) {
                try {
                  if (typeof this._js.consumers === 'object' && typeof this._js.consumers.add === 'function') {
                    console.log('Using newer JetStream API (consumers.add)');
                    return this._js.consumers.add(streamName, config);
                  } else if (typeof this._js.addConsumer === 'function') {
                    console.log('Using older JetStream API (addConsumer)');
                    // @ts-ignore - Support for older JetStream API versions
                    return this._js.addConsumer(streamName, config);
                  } else if (typeof this._js.consumers === 'function') {
                    console.log('Using alternative JetStream API (consumers)');
                    // Some versions expect a different format for creating consumers
                    return this._js.consumers(streamName, config);
                  } else {
                    console.warn('JetStream API does not support adding consumers, using fallback');
                    // Return a mock consumer to avoid errors
                    return {
                      name: config.durable_name,
                      stream_name: streamName,
                      config: config,
                      created: new Date().toISOString(),
                      // Mock fetch method
                      fetch: async () => {
                        console.log('Using mock consumer fetch');
                        return [];
                      },
                      // Mock pull method
                      pull: async () => {
                        console.log('Using mock consumer pull');
                        return [];
                      }
                    };
                  }
                } catch (error) {
                  console.error(`Error in addConsumer for ${streamName}/${config.durable_name}:`, error);
                  // Return a mock consumer to avoid errors
                  return {
                    name: config.durable_name,
                    stream_name: streamName,
                    config: config,
                    created: new Date().toISOString(),
                    // Mock fetch method
                    fetch: async () => {
                      console.log('Using mock consumer fetch');
                      return [];
                    },
                    // Mock pull method
                    pull: async () => {
                      console.log('Using mock consumer pull');
                      return [];
                    }
                  };
                }
              },

              // Method to publish a message
              async publish(subject, data) {
                try {
                  if (typeof this._js.publish === 'function') {
                    console.log('Using JetStream publish');
                    return this._js.publish(subject, data);
                  } else if (this._nc && typeof this._nc.publish === 'function') {
                    console.log('Falling back to regular NATS publish');
                    return this._nc.publish(subject, data);
                  } else {
                    console.warn('No valid publish method found, message not published');
                    // Return a mock ack to avoid errors
                    return { seq: 0 };
                  }
                } catch (error) {
                  console.error(`Error in publish to ${subject}:`, error);
                  // Return a mock ack to avoid errors
                  return { seq: 0 };
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
        const data = await getData(route, js, nc, req);
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
      const data = await getData('alerts/history', js, nc, req);
      res.json(data);
    } catch (error) {
      console.error('Error handling alerts/history request:', error);
      res.status(500).json({ error: 'Failed to fetch historical alerts' });
    }
  });

  app.get('/api/alerts/active', async (req, res) => {
    try {
      const data = await getData('alerts/active', js, nc, req);
      res.json(data);
    } catch (error) {
      console.error('Error handling alerts/active request:', error);
      res.status(500).json({ error: 'Failed to fetch active alerts' });
    }
  });

  // Knowledge base endpoints
  app.get('/api/knowledge/incidents', async (req, res) => {
    try {
      const data = await getData('knowledge/incidents', js, nc, req);
      res.json(data);
    } catch (error) {
      console.error('Error handling knowledge/incidents request:', error);
      res.status(500).json({ error: 'Failed to fetch incidents from knowledge base' });
    }
  });

  app.get('/api/knowledge/postmortems', async (req, res) => {
    try {
      const data = await getData('knowledge/postmortems', js, nc, req);
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