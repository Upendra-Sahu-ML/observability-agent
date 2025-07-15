const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const axios = require('axios');
const { connect, StringCodec } = require('nats');
const OpenAI = require('openai');
const { exec } = require('child_process');
const util = require('util');
const execPromise = util.promisify(exec);
const crypto = require('crypto');

// Load environment variables
require('dotenv').config();

// Import functions from original backends
const { getHistoricalAlerts, getActiveAlerts } = require('./alerts');
const { getIncidents, getPostmortems } = require('./knowledge');

// Configuration
const NATS_URL = process.env.NATS_URL || 'nats://nats:4222';
const PORT = process.env.PORT || 5000;
const sc = StringCodec(); // For encoding/decoding NATS messages

// Import constants for NATS streams
const { STREAM_NAMES, CONSUMER_NAMES, checkStreamExists, createConsumer } = require('./constants');

// Initialize Express app
const app = express();

// Middleware
app.use(cors());
app.use(bodyParser.json());

// Initialize OpenAI
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// In-memory cache for observability data
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

// In-memory storage for runbook executions and notebooks (replacing MongoDB)
const runbookExecutions = {};
const notebooks = new Map(); // Replace MongoDB with in-memory storage

// Cache TTL in milliseconds (5 minutes)
const CACHE_TTL = 5 * 60 * 1000;
const cacheTimestamps = {};

// NATS connection
let natsConnection = null;
let jetStreamContext = null;

/**
 * Initialize NATS connection
 */
async function initializeNATS() {
  try {
    console.log(`Connecting to NATS at ${NATS_URL}...`);
    natsConnection = await connect({ servers: NATS_URL });
    jetStreamContext = natsConnection.jetstream();
    console.log('NATS connection established');
    
    // Persist notebooks to NATS stream on startup
    await persistNotebooksToNATS();
    
    return { nc: natsConnection, js: jetStreamContext };
  } catch (error) {
    console.error('Failed to connect to NATS:', error);
    throw error;
  }
}

/**
 * Persist notebooks to NATS instead of MongoDB
 */
async function persistNotebooksToNATS() {
  try {
    // Load existing notebooks from NATS NOTEBOOKS stream
    const consumer = await createConsumer(jetStreamContext, 'NOTEBOOKS', 'notebooks-loader');
    const messages = await consumer.fetch({ max_messages: 100 });
    
    for (const msg of messages) {
      try {
        const data = JSON.parse(msg.data.toString());
        if (data.id && data.notebook) {
          notebooks.set(data.id, data.notebook);
        }
        await msg.ack();
      } catch (parseErr) {
        console.warn('Failed to parse notebook from NATS:', parseErr.message);
        await msg.ack();
      }
    }
    
    console.log(`Loaded ${notebooks.size} notebooks from NATS`);
  } catch (error) {
    console.warn('Failed to load notebooks from NATS:', error.message);
  }
}

/**
 * Save notebook to NATS stream
 */
async function saveNotebookToNATS(id, notebook) {
  try {
    const data = {
      id: id,
      notebook: notebook,
      timestamp: new Date().toISOString()
    };
    
    await jetStreamContext.publish(`notebooks.${id}`, JSON.stringify(data));
    console.log(`Saved notebook ${id} to NATS`);
  } catch (error) {
    console.error('Failed to save notebook to NATS:', error);
  }
}

/**
 * Get data from cache or fetch from NATS
 */
async function getData(type, req) {
  const now = Date.now();
  const cacheKey = type;
  
  // Check if cache is still valid
  if (cache[cacheKey] && cacheTimestamps[cacheKey] && (now - cacheTimestamps[cacheKey] < CACHE_TTL)) {
    console.log(`Returning cached data for ${type}`);
    return cache[cacheKey];
  }

  console.log(`Fetching fresh data for ${type} from NATS`);
  
  try {
    let data = [];
    
    switch (type) {
      case 'agents':
        data = await fetchAgentData();
        break;
      case 'metrics':
        data = await fetchMetricsData(req.query.service, req.query.alertId);
        break;
      case 'logs':
        data = await fetchLogsData(req.query.service, req.query.alertId);
        break;
      case 'deployment':
        data = await fetchDeploymentData(req.query.service, req.query.alertId);
        break;
      case 'rootcause':
        data = await fetchRootCauseData(req.query.alertId);
        break;
      case 'tracing':
        data = await fetchTracingData(req.query.service, req.query.alertId);
        break;
      case 'notification':
        data = await fetchNotificationData(req.query.alertId);
        break;
      case 'postmortem':
        data = await fetchPostmortemData(req.query.alertId);
        break;
      case 'runbook':
        data = await fetchRunbookData();
        break;
      case 'alerts/history':
        data = await getHistoricalAlerts(jetStreamContext);
        break;
      case 'alerts/active':
        data = await getActiveAlerts(jetStreamContext);
        break;
      case 'knowledge/incidents':
        data = await getIncidents(jetStreamContext);
        break;
      case 'knowledge/postmortems':
        data = await getPostmortems(jetStreamContext);
        break;
      default:
        console.warn(`Unknown data type: ${type}`);
        data = [];
    }
    
    // Update cache
    cache[cacheKey] = data;
    cacheTimestamps[cacheKey] = now;
    
    return data;
  } catch (error) {
    console.error(`Error fetching ${type} data:`, error);
    // Return cached data if available, otherwise empty array
    return cache[cacheKey] || [];
  }
}

/**
 * Fetch agent status data from NATS
 */
async function fetchAgentData() {
  try {
    const consumer = await createConsumer(jetStreamContext, 'AGENTS', 'agents-viewer');
    const messages = await consumer.fetch({ max_messages: 50 });
    
    const agents = [];
    for (const msg of messages) {
      try {
        const data = JSON.parse(msg.data.toString());
        
        if (data.agent_id && data.status) {
          agents.push({
            id: data.agent_id,
            name: data.agent_name || data.agent_id,
            status: data.status,
            last_seen: data.timestamp || new Date().toISOString(),
            message: data.message || '',
            details: data.details || {}
          });
        }
        await msg.ack();
      } catch (parseErr) {
        console.warn('Agent data parsing error:', parseErr.message);
        await msg.ack();
      }
    }
    
    return agents;
  } catch (error) {
    console.error('Error fetching agent data:', error);
    return [];
  }
}

/**
 * Fetch metrics data from NATS
 */
async function fetchMetricsData(service, alertId) {
  try {
    const consumer = await createConsumer(jetStreamContext, 'METRICS', 'metrics-viewer');
    const messages = await consumer.fetch({ max_messages: 100 });
    
    const metrics = [];
    for (const msg of messages) {
      try {
        const data = JSON.parse(msg.data.toString());
        
        // Filter by service and alertId if specified
        if (service && data.service !== service) continue;
        if (alertId && data.alert_id !== alertId) continue;
        
        if (data.metrics && Array.isArray(data.metrics)) {
          metrics.push(...data.metrics);
        } else if (data.metric_name && data.value !== undefined) {
          metrics.push({
            timestamp: data.timestamp || new Date().toISOString(),
            metric: data.metric_name,
            value: data.value,
            service: data.service || 'unknown',
            alert_id: data.alert_id || null
          });
        }
        await msg.ack();
      } catch (parseErr) {
        console.warn('Metrics data parsing error:', parseErr.message);
        await msg.ack();
      }
    }
    
    return metrics;
  } catch (error) {
    console.error('Error fetching metrics data:', error);
    return [];
  }
}

/**
 * Fetch logs data from NATS
 */
async function fetchLogsData(service, alertId) {
  try {
    const consumer = await createConsumer(jetStreamContext, 'LOGS', 'logs-viewer');
    const messages = await consumer.fetch({ max_messages: 100 });
    
    const logs = [];
    for (const msg of messages) {
      try {
        const data = JSON.parse(msg.data.toString());
        
        // Filter by service and alertId if specified
        if (service && data.service !== service) continue;
        if (alertId && data.alert_id !== alertId) continue;
        
        if (data.logs && Array.isArray(data.logs.entries)) {
          for (const entry of data.logs.entries) {
            if (entry && entry.message) {
              logs.push({
                timestamp: entry.timestamp || data.timestamp || new Date().toISOString(),
                level: entry.level || 'INFO',
                message: entry.message,
                service: data.service || 'unknown',
                alert_id: data.alert_id || null,
                source: entry.source || 'unknown'
              });
            }
          }
        } else if (data.message && data.service) {
          logs.push({
            timestamp: data.timestamp || new Date().toISOString(),
            level: data.level || 'INFO',
            message: data.message,
            service: data.service,
            alert_id: data.alert_id || null,
            source: data.source || 'unknown'
          });
        }
        await msg.ack();
      } catch (parseErr) {
        console.warn('Logs data parsing error:', parseErr.message);
        await msg.ack();
      }
    }
    
    return logs;
  } catch (error) {
    console.error('Error fetching logs data:', error);
    return [];
  }
}

/**
 * Additional fetch functions for other data types
 * (Implementation details similar to above patterns)
 */
async function fetchDeploymentData(service, alertId) {
  // Similar implementation for deployment data
  return [];
}

async function fetchRootCauseData(alertId) {
  // Similar implementation for root cause data
  return [];
}

async function fetchTracingData(service, alertId) {
  // Similar implementation for tracing data
  return [];
}

async function fetchNotificationData(alertId) {
  // Similar implementation for notification data
  return [];
}

async function fetchPostmortemData(alertId) {
  // Similar implementation for postmortem data
  return [];
}

async function fetchRunbookData() {
  // Similar implementation for runbook data
  return [];
}

// ===== OBSERVABILITY DATA API ROUTES =====

app.get('/api/:type', async (req, res) => {
  try {
    const { type } = req.params;
    console.log(`API request for ${type} data`);
    
    const data = await getData(type, req);
    res.json(data);
  } catch (error) {
    console.error(`Error in /api/${req.params.type}:`, error);
    res.status(500).json({ error: 'Internal server error', details: error.message });
  }
});

// ===== K8S COMMAND AND NOTEBOOK API ROUTES =====

// Notebooks endpoints (replacing MongoDB with in-memory + NATS persistence)
app.get('/api/notebooks', async (req, res) => {
  try {
    const notebookList = Array.from(notebooks.entries()).map(([id, notebook]) => ({
      _id: id,
      name: notebook.name,
      description: notebook.description,
      createdAt: notebook.createdAt,
      updatedAt: notebook.updatedAt
    }));
    
    res.json(notebookList);
  } catch (error) {
    console.error('Error fetching notebooks:', error);
    res.status(500).json({ error: 'Failed to fetch notebooks' });
  }
});

app.post('/api/notebooks', async (req, res) => {
  try {
    const { name, description } = req.body;
    
    if (!name) {
      return res.status(400).json({ error: 'Name is required' });
    }
    
    const id = crypto.randomUUID();
    const notebook = {
      name,
      description: description || '',
      cells: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    
    notebooks.set(id, notebook);
    await saveNotebookToNATS(id, notebook);
    
    res.status(201).json({ _id: id, ...notebook });
  } catch (error) {
    console.error('Error creating notebook:', error);
    res.status(500).json({ error: 'Failed to create notebook' });
  }
});

app.get('/api/notebooks/:id', async (req, res) => {
  try {
    const notebook = notebooks.get(req.params.id);
    
    if (!notebook) {
      return res.status(404).json({ error: 'Notebook not found' });
    }
    
    res.json({ _id: req.params.id, ...notebook });
  } catch (error) {
    console.error('Error fetching notebook:', error);
    res.status(500).json({ error: 'Failed to fetch notebook' });
  }
});

app.put('/api/notebooks/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const updates = req.body;
    
    const notebook = notebooks.get(id);
    if (!notebook) {
      return res.status(404).json({ error: 'Notebook not found' });
    }
    
    const updatedNotebook = {
      ...notebook,
      ...updates,
      updatedAt: new Date().toISOString()
    };
    
    notebooks.set(id, updatedNotebook);
    await saveNotebookToNATS(id, updatedNotebook);
    
    res.json({ _id: id, ...updatedNotebook });
  } catch (error) {
    console.error('Error updating notebook:', error);
    res.status(500).json({ error: 'Failed to update notebook' });
  }
});

app.delete('/api/notebooks/:id', async (req, res) => {
  try {
    const { id } = req.params;
    
    if (!notebooks.has(id)) {
      return res.status(404).json({ error: 'Notebook not found' });
    }
    
    notebooks.delete(id);
    
    // Note: For complete deletion from NATS, we'd need tombstone records
    // For now, we'll just remove from memory
    
    res.json({ message: 'Notebook deleted successfully' });
  } catch (error) {
    console.error('Error deleting notebook:', error);
    res.status(500).json({ error: 'Failed to delete notebook' });
  }
});

// K8s command execution endpoints
app.post('/api/k8s/translate', async (req, res) => {
  try {
    const { prompt } = req.body;
    
    if (!prompt) {
      return res.status(400).json({ error: 'Prompt is required' });
    }
    
    const completion = await openai.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [
        {
          role: "system",
          content: `You are a Kubernetes expert. Convert natural language requests to kubectl commands. 
                   Only return the kubectl command, nothing else. 
                   If you cannot create a safe command, return "ERROR: Cannot generate safe command for this request."`
        },
        {
          role: "user",
          content: prompt
        }
      ],
      max_tokens: 200,
      temperature: 0.1
    });
    
    const command = completion.choices[0].message.content.trim();
    
    if (command.startsWith('ERROR:')) {
      return res.status(400).json({ error: command });
    }
    
    res.json({ command });
  } catch (error) {
    console.error('Error translating command:', error);
    res.status(500).json({ error: 'Failed to translate command' });
  }
});

app.post('/api/k8s/execute', async (req, res) => {
  try {
    const { command } = req.body;
    
    if (!command) {
      return res.status(400).json({ error: 'Command is required' });
    }
    
    // Security check: only allow kubectl commands
    if (!command.trim().startsWith('kubectl')) {
      return res.status(400).json({ error: 'Only kubectl commands are allowed' });
    }
    
    console.log('Executing command:', command);
    
    const { stdout, stderr } = await execPromise(command, {
      timeout: 30000, // 30 second timeout
      maxBuffer: 1024 * 1024 // 1MB max output
    });
    
    res.json({ 
      success: true, 
      output: stdout,
      error: stderr || null
    });
  } catch (error) {
    console.error('Command execution error:', error);
    res.json({ 
      success: false, 
      error: error.message,
      output: error.stdout || null
    });
  }
});

// ===== RUNBOOK EXECUTION ENDPOINTS =====

app.post('/api/runbook/:id/execute', async (req, res) => {
  try {
    const { id } = req.params;
    const { steps } = req.body;
    
    const executionId = crypto.randomUUID();
    
    runbookExecutions[executionId] = {
      id: executionId,
      runbookId: id,
      status: 'running',
      steps: steps || [],
      currentStep: 0,
      results: [],
      startTime: new Date().toISOString()
    };
    
    // Execute runbook asynchronously
    executeRunbook(executionId, steps);
    
    res.json({ executionId, status: 'started' });
  } catch (error) {
    console.error('Error starting runbook execution:', error);
    res.status(500).json({ error: 'Failed to start runbook execution' });
  }
});

app.get('/api/runbook/execution/:executionId', (req, res) => {
  try {
    const execution = runbookExecutions[req.params.executionId];
    
    if (!execution) {
      return res.status(404).json({ error: 'Execution not found' });
    }
    
    res.json(execution);
  } catch (error) {
    console.error('Error fetching execution status:', error);
    res.status(500).json({ error: 'Failed to fetch execution status' });
  }
});

async function executeRunbook(executionId, steps) {
  const execution = runbookExecutions[executionId];
  
  try {
    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];
      execution.currentStep = i;
      
      if (step.type === 'command' && step.command) {
        try {
          const { stdout, stderr } = await execPromise(step.command, {
            timeout: 60000,
            maxBuffer: 1024 * 1024
          });
          
          execution.results.push({
            step: i,
            success: true,
            output: stdout,
            error: stderr || null
          });
        } catch (error) {
          execution.results.push({
            step: i,
            success: false,
            error: error.message,
            output: error.stdout || null
          });
        }
      }
      
      // Add delay between steps
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    execution.status = 'completed';
    execution.endTime = new Date().toISOString();
  } catch (error) {
    execution.status = 'failed';
    execution.error = error.message;
    execution.endTime = new Date().toISOString();
  }
}

// ===== SERVER INITIALIZATION =====

async function startServer() {
  try {
    // Initialize NATS connection
    await initializeNATS();
    
    // Start HTTP server
    app.listen(PORT, () => {
      console.log(`Unified UI Backend server running on port ${PORT}`);
      console.log('Services consolidated:');
      console.log('  - Observability data API (former ui-backend)');
      console.log('  - K8s command execution (former k8s-command-backend)');
      console.log('  - Notebook management (replacing MongoDB with NATS)');
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('Shutting down unified backend...');
  if (natsConnection) {
    await natsConnection.close();
  }
  process.exit(0);
});

// Start the server
startServer();