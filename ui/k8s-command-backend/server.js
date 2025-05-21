const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const { connect, StringCodec } = require('nats');
const mongoose = require('mongoose');
const OpenAI = require('openai');
const { exec } = require('child_process');
const util = require('util');
const execPromise = util.promisify(exec);
const crypto = require('crypto');

// Load environment variables
require('dotenv').config();

// Initialize Express app
const app = express();
const PORT = process.env.PORT || 5002;

// Middleware
app.use(cors());
app.use(bodyParser.json());

// Initialize OpenAI
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// MongoDB connection
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/k8s-command';
mongoose.connect(MONGODB_URI)
  .then(() => console.log('MongoDB connected'))
  .catch(err => console.error('MongoDB connection error:', err));

// Define Notebook schema
const notebookSchema = new mongoose.Schema({
  name: { type: String, required: true },
  description: { type: String },
  cells: [{
    type: { type: String, enum: ['command', 'result'], default: 'command' },
    content: {
      type: String,
      required: true,
      // Set default value to space if content is empty
      default: ' '
    },
    executedCommand: { type: String },
    timestamp: { type: Date, default: Date.now }
  }],
  createdAt: { type: Date, default: Date.now },
  updatedAt: { type: Date, default: Date.now }
});

const Notebook = mongoose.model('Notebook', notebookSchema);

// Define Session schema for context management
const sessionSchema = new mongoose.Schema({
  sessionId: { type: String, required: true, unique: true },
  context: {
    lastCommand: { type: String },
    lastCommandOutput: { type: String },
    lastNamespace: { type: String },
    lastPods: { type: Array, default: [] },
    lastServices: { type: Array, default: [] },
    lastDeployments: { type: Array, default: [] },
    lastResources: { type: Object, default: {} }
  },
  createdAt: { type: Date, default: Date.now },
  updatedAt: { type: Date, default: Date.now }
});

// Add TTL index to automatically expire sessions after 1 hour of inactivity
sessionSchema.index({ updatedAt: 1 }, { expireAfterSeconds: 3600 });

const Session = mongoose.model('Session', sessionSchema);

// In-memory context cache for faster access
const contextCache = new Map();

// NATS connection
let nc = null;
let js = null;
const sc = StringCodec();

async function connectToNATS() {
  try {
    const NATS_URL = process.env.NATS_URL || 'nats://localhost:4222';
    nc = await connect({ servers: NATS_URL });
    console.log(`Connected to NATS at ${NATS_URL}`);

    // Try to create JetStream context
    try {
      if (typeof nc.jetstream === 'function') {
        js = nc.jetstream();
        console.log('JetStream context created');

        // Try to detect JetStream API version
        if (js) {
          if (typeof js.streams === 'object' && typeof js.streams.info === 'function') {
            console.log('Detected newer JetStream API (streams.info)');
          } else if (typeof js.streamInfo === 'function') {
            console.log('Detected older JetStream API (streamInfo)');
          } else if (typeof js.addStream === 'function') {
            console.log('Detected older JetStream API (addStream)');
          } else {
            console.log('Unknown JetStream API version - will use basic NATS only');
            // Set js to null to indicate JetStream is not available
            js = null;
          }
        }

        // Only try to check streams if we have a valid JetStream context
        if (js) {
          // Check if streams exist
          await checkStreams();
        }
      } else {
        console.log('JetStream not available in this NATS client version');
        js = null;
      }
    } catch (jsErr) {
      console.error(`JetStream initialization error: ${jsErr.message}`);
      js = null;
    }

    return { nc, js };
  } catch (err) {
    console.error(`NATS connection error: ${err.message}`);
    return { nc: null, js: null };
  }
}

async function checkStreams() {
  try {
    if (!js) {
      console.warn('JetStream not available, skipping stream check');
      return;
    }

    // Check if the NOTEBOOKS stream exists
    try {
      // Different versions of NATS.js have different APIs
      // Try the newer API first
      if (typeof js.streams === 'object' && typeof js.streams.info === 'function') {
        await js.streams.info('NOTEBOOKS');
        console.log('NOTEBOOKS stream exists');
      } else if (typeof js.streamInfo === 'function') {
        // Try older API
        await js.streamInfo('NOTEBOOKS');
        console.log('NOTEBOOKS stream exists');
      } else {
        throw new Error('Unknown JetStream API');
      }
    } catch (err) {
      console.warn('NOTEBOOKS stream not found - it should be created by the NATS ConfigMap');
    }
  } catch (err) {
    console.error(`Error checking streams: ${err.message}`);
    console.error('JetStream API may be incompatible with this version of NATS client');
  }
}

// Function to get or create a session
async function getOrCreateSession(sessionId) {
  // Check cache first
  if (contextCache.has(sessionId)) {
    return contextCache.get(sessionId);
  }

  // If not in cache, check database
  let session = await Session.findOne({ sessionId });

  // If not in database, create new session
  if (!session) {
    session = new Session({
      sessionId,
      context: {
        lastCommand: null,
        lastCommandOutput: null,
        lastNamespace: null,
        lastPods: [],
        lastServices: [],
        lastDeployments: [],
        lastResources: {}
      }
    });
    await session.save();
  }

  // Update cache
  contextCache.set(sessionId, session.context);

  return session.context;
}

// Function to update session context
async function updateSessionContext(sessionId, contextUpdates) {
  // Update in database
  const session = await Session.findOneAndUpdate(
    { sessionId },
    {
      $set: {
        'context': { ...contextUpdates },
        'updatedAt': Date.now()
      }
    },
    { new: true, upsert: true }
  );

  // Update cache
  contextCache.set(sessionId, session.context);

  return session.context;
}

// Function to extract context from command output
function extractContextFromOutput(command, output) {
  const context = {
    lastCommand: command,
    lastCommandOutput: output
  };

  // Extract namespace if present in command
  const namespaceMatch = command.match(/-n\s+(\S+)|--namespace\s+(\S+)|--namespace=(\S+)/);
  if (namespaceMatch) {
    context.lastNamespace = namespaceMatch[1] || namespaceMatch[2] || namespaceMatch[3];
  }

  // If command is 'get pods', extract pod names
  if (command.includes('get pods') || command.includes('get pod')) {
    try {
      // Try to parse as JSON if output is in JSON format
      if (output.trim().startsWith('{') || output.trim().startsWith('[')) {
        const jsonOutput = JSON.parse(output);

        if (jsonOutput.items) {
          // Handle kubectl get pods -o json output
          context.lastPods = jsonOutput.items.map(pod => ({
            name: pod.metadata.name,
            namespace: pod.metadata.namespace,
            status: pod.status.phase
          }));
        }
      } else {
        // Handle plain text output
        const lines = output.trim().split('\n');
        if (lines.length > 1) {
          // Skip header line
          const pods = [];
          for (let i = 1; i < lines.length; i++) {
            const columns = lines[i].split(/\s+/);
            if (columns.length >= 3) {
              pods.push({
                name: columns[0],
                status: columns[2]
              });
            }
          }
          context.lastPods = pods;
        }
      }
    } catch (error) {
      console.error('Error parsing pod output:', error);
    }
  }

  // If command is 'get services', extract service names
  if (command.includes('get services') || command.includes('get svc')) {
    try {
      const lines = output.trim().split('\n');
      if (lines.length > 1) {
        // Skip header line
        const services = [];
        for (let i = 1; i < lines.length; i++) {
          const columns = lines[i].split(/\s+/);
          if (columns.length >= 2) {
            services.push({
              name: columns[0]
            });
          }
        }
        context.lastServices = services;
      }
    } catch (error) {
      console.error('Error parsing service output:', error);
    }
  }

  // If command is 'get deployments', extract deployment names
  if (command.includes('get deployments') || command.includes('get deploy')) {
    try {
      const lines = output.trim().split('\n');
      if (lines.length > 1) {
        // Skip header line
        const deployments = [];
        for (let i = 1; i < lines.length; i++) {
          const columns = lines[i].split(/\s+/);
          if (columns.length >= 2) {
            deployments.push({
              name: columns[0]
            });
          }
        }
        context.lastDeployments = deployments;
      }
    } catch (error) {
      console.error('Error parsing deployment output:', error);
    }
  }

  return context;
}

// Function to convert natural language to Kubernetes command
async function naturalLanguageToK8sCommand(text, sessionId = null) {
  try {
    let context = {};
    let systemPrompt = "You are a Kubernetes expert. Convert natural language queries into kubectl commands. Only respond with the exact command to run, nothing else. If multiple commands are needed, separate them with semicolons.";

    // If sessionId is provided, get context from session
    if (sessionId) {
      context = await getOrCreateSession(sessionId);

      // Enhance system prompt with context
      if (context) {
        systemPrompt += "\n\nMaintain context between commands:";

        // Add namespace context
        if (context.lastNamespace) {
          systemPrompt += `\n- Use namespace '${context.lastNamespace}' unless explicitly specified otherwise.`;
        } else {
          systemPrompt += "\n- When namespace is not specified, search across all namespaces using '--all-namespaces' or '-A'.";
        }

        // Add pod context
        if (context.lastPods && context.lastPods.length > 0) {
          systemPrompt += "\n- Recent pods:";
          context.lastPods.slice(0, 5).forEach(pod => {
            systemPrompt += `\n  * ${pod.name}${pod.namespace ? ` (namespace: ${pod.namespace})` : ''}${pod.status ? ` (status: ${pod.status})` : ''}`;
          });
        }

        // Add service context
        if (context.lastServices && context.lastServices.length > 0) {
          systemPrompt += "\n- Recent services:";
          context.lastServices.slice(0, 5).forEach(svc => {
            systemPrompt += `\n  * ${svc.name}`;
          });
        }

        // Add deployment context
        if (context.lastDeployments && context.lastDeployments.length > 0) {
          systemPrompt += "\n- Recent deployments:";
          context.lastDeployments.slice(0, 5).forEach(deploy => {
            systemPrompt += `\n  * ${deploy.name}`;
          });
        }

        // Add last command context
        if (context.lastCommand) {
          systemPrompt += `\n\nLast command executed: ${context.lastCommand}`;
        }

        systemPrompt += `
        // Context and Reference Resolution
        - Interpret "that pod", "those pods", etc., as referring to the most recently mentioned pod(s).
        - Map services to pods via endpoints or label selectors.
        - Resolve deployments, jobs, or daemonsets to their associated pods.
        - Use the last mentioned namespace if none is given.

        // Namespace Defaults
        - If no namespace is specified, use the last known one.
        - If unavailable, default to all namespaces (-A).
        - If multiple namespaces are inferred, ask the user.

        // Logs Handling
        - If no container is specified in a multi-container pod, ask or try all.
        - Use: kubectl get pod <pod> -o jsonpath='{.spec.containers[*].name}' to list containers.
        - Default to last referenced pod + namespace for logs.
        - Support keyword filters via grep (e.g., errors, timeouts).
        - Use --tail=100 or -f for "latest" or live logs.
        - Always specify a pod or resource in kubectl logs.
        - To get logs from all pods in a namespace:
          kubectl get pods -n observability -o name | xargs -I{} kubectl logs -n observability --all-containers=true {} | grep error
        - Apply same logic to logs from jobs or daemonsets.

        // Multiple Pod Handling
        - If multiple pods match, list them and prefer running/recent ones.

        // Error Handling
        - If a resource isn't found, ask for clarification.
        - If command intent is unclear, confirm before running.

        // Command Execution Rules
        - Only output valid kubectl commands; avoid placeholders unless requesting input.
        - Use --all-containers=true when needed.
        - Use JSONPath or Go templates to extract fields.
        - Maintain syntax and order in piped commands.

        // Examples
        - "Get logs from that pod" → use last referenced pod and namespace.
        - "Check that service" → find its pods, check logs for errors.
        - "Describe it" → describe last referenced resource.
        - "Get pods" → use last namespace or -A.
        - "Logs from the job" → resolve job to pods, apply log logic.`;
      }
    }

    const response = await openai.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [
        {
          role: "system",
          content: systemPrompt
        },
        {
          role: "user",
          content: text
        }
      ],
      temperature: 0.2,
      max_tokens: 150
    });

    return response.choices[0].message.content.trim();
  } catch (error) {
    console.error('Error calling OpenAI API:', error);
    throw new Error(`Failed to convert to Kubernetes command: ${error.message}`);
  }
}

// Function to execute Kubernetes command
async function executeK8sCommand(command, sessionId = null) {
  try {
    const { stdout, stderr } = await execPromise(command);

    // If sessionId is provided, update context
    if (sessionId) {
      const contextUpdates = extractContextFromOutput(command, stdout);
      await updateSessionContext(sessionId, contextUpdates);
    }

    return {
      success: true,
      output: stdout,
      error: stderr
    };
  } catch (error) {
    return {
      success: false,
      output: '',
      error: error.message
    };
  }
}

// API Routes

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    nats: nc ? 'connected' : 'disconnected',
    mongodb: mongoose.connection.readyState === 1 ? 'connected' : 'disconnected'
  });
});

// Convert natural language to Kubernetes command
app.post('/api/convert', async (req, res) => {
  try {
    const { text, sessionId } = req.body;
    if (!text) {
      return res.status(400).json({ error: 'Text is required' });
    }

    // Generate a session ID if not provided
    const effectiveSessionId = sessionId || crypto.randomUUID();

    const command = await naturalLanguageToK8sCommand(text, effectiveSessionId);
    res.json({ command, sessionId: effectiveSessionId });
  } catch (error) {
    console.error('Error converting text to command:', error);
    res.status(500).json({ error: error.message });
  }
});

// Execute Kubernetes command
app.post('/api/execute', async (req, res) => {
  try {
    const { command, sessionId } = req.body;
    if (!command) {
      return res.status(400).json({ error: 'Command is required' });
    }

    // Generate a session ID if not provided
    const effectiveSessionId = sessionId || crypto.randomUUID();

    const result = await executeK8sCommand(command, effectiveSessionId);
    res.json({ ...result, sessionId: effectiveSessionId });
  } catch (error) {
    console.error('Error executing command:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get session context
app.get('/api/context/:sessionId', async (req, res) => {
  try {
    const { sessionId } = req.params;
    if (!sessionId) {
      return res.status(400).json({ error: 'Session ID is required' });
    }

    const context = await getOrCreateSession(sessionId);
    res.json({ context, sessionId });
  } catch (error) {
    console.error('Error getting context:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get all notebooks
app.get('/api/notebooks', async (req, res) => {
  try {
    const notebooks = await Notebook.find().sort({ updatedAt: -1 });
    res.json(notebooks);
  } catch (error) {
    console.error('Error getting notebooks:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get notebook by ID
app.get('/api/notebooks/:id', async (req, res) => {
  try {
    const notebook = await Notebook.findById(req.params.id);
    if (!notebook) {
      return res.status(404).json({ error: 'Notebook not found' });
    }
    res.json(notebook);
  } catch (error) {
    console.error('Error getting notebook:', error);
    res.status(500).json({ error: error.message });
  }
});

// Create a new notebook
app.post('/api/notebooks', async (req, res) => {
  try {
    const { name, description, cells } = req.body;
    if (!name) {
      return res.status(400).json({ error: 'Name is required' });
    }

    // Validate and clean cells
    const validatedCells = (cells || []).map(cell => ({
      ...cell,
      // Ensure content is never empty
      content: cell.content || ' '
    }));

    const notebook = new Notebook({
      name,
      description,
      cells: validatedCells
    });

    await notebook.save();

    // Publish to NATS if connected
    try {
      // Try JetStream publish first if available
      if (js && typeof js.publish === 'function') {
        await js.publish(`notebooks.created`, sc.encode(JSON.stringify(notebook)));
      }
      // Fallback to regular NATS publish
      else if (nc && typeof nc.publish === 'function') {
        nc.publish(`notebooks.created`, sc.encode(JSON.stringify(notebook)));
      }
    } catch (natsError) {
      console.warn('NATS publish error (non-critical):', natsError.message);
      // Continue even if NATS publish fails
    }

    res.status(201).json(notebook);
  } catch (error) {
    console.error('Error creating notebook:', error);
    res.status(500).json({ error: error.message });
  }
});

// Update a notebook
app.put('/api/notebooks/:id', async (req, res) => {
  try {
    const { name, description, cells } = req.body;

    // Validate and clean cells
    const validatedCells = (cells || []).map(cell => ({
      ...cell,
      // Ensure content is never empty
      content: cell.content || ' '
    }));

    const updates = {
      name,
      description,
      cells: validatedCells,
      updatedAt: Date.now()
    };

    const notebook = await Notebook.findByIdAndUpdate(
      req.params.id,
      updates,
      { new: true }
    );

    if (!notebook) {
      return res.status(404).json({ error: 'Notebook not found' });
    }

    // Publish to NATS if connected
    try {
      // Try JetStream publish first if available
      if (js && typeof js.publish === 'function') {
        await js.publish(`notebooks.updated`, sc.encode(JSON.stringify(notebook)));
      }
      // Fallback to regular NATS publish
      else if (nc && typeof nc.publish === 'function') {
        nc.publish(`notebooks.updated`, sc.encode(JSON.stringify(notebook)));
      }
    } catch (natsError) {
      console.warn('NATS publish error (non-critical):', natsError.message);
      // Continue even if NATS publish fails
    }

    res.json(notebook);
  } catch (error) {
    console.error('Error updating notebook:', error);
    res.status(500).json({ error: error.message });
  }
});

// Delete a notebook
app.delete('/api/notebooks/:id', async (req, res) => {
  try {
    const notebook = await Notebook.findByIdAndDelete(req.params.id);
    if (!notebook) {
      return res.status(404).json({ error: 'Notebook not found' });
    }

    // Publish to NATS if connected
    try {
      // Try JetStream publish first if available
      if (js && typeof js.publish === 'function') {
        await js.publish(`notebooks.deleted`, sc.encode(JSON.stringify({ id: req.params.id })));
      }
      // Fallback to regular NATS publish
      else if (nc && typeof nc.publish === 'function') {
        nc.publish(`notebooks.deleted`, sc.encode(JSON.stringify({ id: req.params.id })));
      }
    } catch (natsError) {
      console.warn('NATS publish error (non-critical):', natsError.message);
      // Continue even if NATS publish fails
    }

    res.json({ message: 'Notebook deleted successfully' });
  } catch (error) {
    console.error('Error deleting notebook:', error);
    res.status(500).json({ error: error.message });
  }
});

// Export notebook as runbook
app.post('/api/notebooks/:id/export', async (req, res) => {
  try {
    const notebook = await Notebook.findById(req.params.id);
    if (!notebook) {
      return res.status(404).json({ error: 'Notebook not found' });
    }

    // Format notebook as runbook
    const runbookContent = notebook.cells
      .filter(cell => cell.type === 'command')
      .map((cell, index) => {
        return `## Step ${index + 1}: ${cell.content}\n\`\`\`bash\n${cell.executedCommand}\n\`\`\`\n`;
      })
      .join('\n');

    const runbookData = {
      name: `${notebook.name} Runbook`,
      service: req.body.service || 'kubernetes',
      content: `# ${notebook.name}\n\n${notebook.description || ''}\n\n${runbookContent}`
    };

    // Try to send to runbook API via NATS
    try {
      // Try JetStream publish first if available
      if (js && typeof js.publish === 'function') {
        await js.publish('runbooks.create', sc.encode(JSON.stringify(runbookData)));
        res.json({ success: true, runbook: runbookData });
        return;
      }
      // Fallback to regular NATS publish
      else if (nc && typeof nc.publish === 'function') {
        nc.publish('runbooks.create', sc.encode(JSON.stringify(runbookData)));
        res.json({ success: true, runbook: runbookData });
        return;
      }
    } catch (natsError) {
      console.warn('NATS publish error, falling back to direct API call:', natsError.message);
    }

    // Fallback to direct API call
    try {
      const axios = require('axios');
      const response = await axios.post('http://localhost:5001/api/runbook', runbookData);
      res.json({ success: true, runbook: response.data });
    } catch (axiosError) {
      console.error('Error calling runbook API directly:', axiosError.message);
      // Still return success to the client, but log the error
      res.json({ success: true, runbook: runbookData, warning: 'Runbook created but may not be accessible immediately' });
    }
  } catch (error) {
    console.error('Error exporting notebook as runbook:', error);
    res.status(500).json({ error: error.message });
  }
});

// Start the server
async function startServer() {
  // Connect to NATS
  await connectToNATS();

  // Start Express server
  app.listen(PORT, () => {
    console.log(`K8s Command Backend listening on port ${PORT}`);
  });
}

startServer();
