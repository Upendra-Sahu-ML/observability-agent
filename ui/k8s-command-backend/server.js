const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const { connect, StringCodec } = require('nats');
const mongoose = require('mongoose');
const OpenAI = require('openai');
const { exec } = require('child_process');
const util = require('util');
const execPromise = util.promisify(exec);

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
    content: { type: String, required: true },
    executedCommand: { type: String },
    timestamp: { type: Date, default: Date.now }
  }],
  createdAt: { type: Date, default: Date.now },
  updatedAt: { type: Date, default: Date.now }
});

const Notebook = mongoose.model('Notebook', notebookSchema);

// NATS connection
let nc = null;
let js = null;
const sc = StringCodec();

async function connectToNATS() {
  try {
    const NATS_URL = process.env.NATS_URL || 'nats://localhost:4222';
    nc = await connect({ servers: NATS_URL });
    console.log(`Connected to NATS at ${NATS_URL}`);
    
    // Create JetStream context
    js = nc.jetstream();
    
    // Create streams if they don't exist
    await createStreams();
    
    return { nc, js };
  } catch (err) {
    console.error(`NATS connection error: ${err.message}`);
    return { nc: null, js: null };
  }
}

async function createStreams() {
  try {
    // Create a stream for notebooks
    await js.streams.add({ name: 'NOTEBOOKS', subjects: ['notebooks.*'] });
    console.log('NOTEBOOKS stream created or already exists');
  } catch (err) {
    if (err.code !== 400) { // 400 means the stream already exists
      console.error(`Error creating streams: ${err.message}`);
    }
  }
}

// Function to convert natural language to Kubernetes command
async function naturalLanguageToK8sCommand(text) {
  try {
    const response = await openai.chat.completions.create({
      model: "gpt-4",
      messages: [
        {
          role: "system",
          content: "You are a Kubernetes expert. Convert natural language queries into kubectl commands. Only respond with the exact command to run, nothing else. If multiple commands are needed, separate them with semicolons."
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
async function executeK8sCommand(command) {
  try {
    const { stdout, stderr } = await execPromise(command);
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
    const { text } = req.body;
    if (!text) {
      return res.status(400).json({ error: 'Text is required' });
    }

    const command = await naturalLanguageToK8sCommand(text);
    res.json({ command });
  } catch (error) {
    console.error('Error converting text to command:', error);
    res.status(500).json({ error: error.message });
  }
});

// Execute Kubernetes command
app.post('/api/execute', async (req, res) => {
  try {
    const { command } = req.body;
    if (!command) {
      return res.status(400).json({ error: 'Command is required' });
    }

    const result = await executeK8sCommand(command);
    res.json(result);
  } catch (error) {
    console.error('Error executing command:', error);
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

    const notebook = new Notebook({
      name,
      description,
      cells: cells || []
    });

    await notebook.save();

    // Publish to NATS if connected
    if (js) {
      await js.publish(`notebooks.created`, sc.encode(JSON.stringify(notebook)));
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
    const updates = {
      name,
      description,
      cells,
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
    if (js) {
      await js.publish(`notebooks.updated`, sc.encode(JSON.stringify(notebook)));
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
    if (js) {
      await js.publish(`notebooks.deleted`, sc.encode(JSON.stringify({ id: req.params.id })));
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

    // Send to runbook API if NATS is connected
    if (js) {
      await js.publish('runbooks.create', sc.encode(JSON.stringify(runbookData)));
      res.json({ success: true, runbook: runbookData });
    } else {
      // Fallback to direct API call
      const axios = require('axios');
      const response = await axios.post('http://localhost:5001/api/runbook', runbookData);
      res.json({ success: true, runbook: response.data });
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
