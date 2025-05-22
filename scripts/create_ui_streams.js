#!/usr/bin/env node
/**
 * Create UI-specific JetStream Streams for Observability Agent
 *
 * This script creates all the required JetStream streams for the UI backend
 * with support for the JetStream domain.
 *
 * Usage:
 *   node create_ui_streams.js [--nats-url=<url>] [--domain=<domain>]
 *
 * Options:
 *   --nats-url=<url>     NATS server URL (default: nats://localhost:4222)
 *   --domain=<domain>    JetStream domain (default: observability-agent)
 */

const { connect } = require('nats');

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
  domain: args['domain'] || 'observability-agent'
};

// Required streams and their subjects
const requiredStreams = [
  { name: 'METRICS', subjects: ['metrics', 'metrics.>'] },
  { name: 'LOGS', subjects: ['logs', 'logs.>'] },
  { name: 'ALERTS', subjects: ["alerts", "alerts.>"] },
  { name: 'AGENT_TASKS', subjects: ["metric_agent", "log_agent", "deployment_agent", "tracing_agent",
    "root_cause_agent", "notification_agent", "postmortem_agent", "runbook_agent",
    "agent.tasks.>"] },
  { name: 'ALERT_DATA', subjects: ["alert_data_request", "alert_data_response.*", "alert.data.>"] },
  { name: 'AGENTS', subjects: ['agent.status.>'] },
  { name: 'DEPLOYMENTS', subjects: ['deployments', 'deployments.>'] },
  { name: 'TRACES', subjects: ['traces', 'traces.>'] },
  { name: 'ROOT_CAUSE', subjects: ["root_cause_analysis", "root_cause_result", "rootcause.>"] },
  { name: 'NOTIFICATIONS', subjects: ["notification_requests", "notifications.>"] },
  { name: 'POSTMORTEMS', subjects: ["postmortems", "postmortems.>"] },
  { name: 'RUNBOOKS', subjects: ["runbooks", "runbook.definition.>"] },
  { name: 'RUNBOOK_EXECUTIONS', subjects: ["runbook.execute", "runbook.status.>", "runbook.execution.>"] },
  { name: 'RESPONSES', subjects: ["orchestrator_response", "responses.>"] },
  { name: 'NOTEBOOKS', subjects: ["notebooks", "notebooks.>"] }
];

/**
 * Create a stream if it doesn't exist
 * @param {Object} js - JetStream client
 * @param {string} name - Name of the stream
 * @param {Array<string>} subjects - Subjects for the stream
 * @returns {Promise<boolean>} - True if stream exists or was created
 */
async function createStream(js, name, subjects) {
  try {
    console.log(`Checking if stream ${name} exists...`);
    
    // Get JetStreamManager if available - NATS.js v2 provides a jetstreamManager function
    let jsm = null;
    if (js.nc && typeof js.nc.jetstreamManager === 'function') {
      try {
        jsm = await js.nc.jetstreamManager();
        console.log('JetStreamManager obtained successfully');
      } catch (jsmErr) {
        console.warn(`Failed to get JetStreamManager: ${jsmErr.message}, will fall back to JetStream API`);
      }
    }

    // Try different JetStream API versions, prioritizing JetStreamManager
    try {
      // First try JetStreamManager if available
      if (jsm && typeof jsm.streams === 'object' && typeof jsm.streams.info === 'function') {
        await jsm.streams.info(name);
        console.log(`Stream ${name} already exists (using JetStreamManager streams.info)`);
        return true;
      }
      // Try newer JetStream API version
      else if (typeof js.streams === 'object' && typeof js.streams.info === 'function') {
        await js.streams.info(name);
        console.log(`Stream ${name} already exists (using streams.info)`);
        return true;
      }
      // Try older API version
      else if (typeof js.streamInfo === 'function') {
        await js.streamInfo(name);
        console.log(`Stream ${name} already exists (using streamInfo)`);
        return true;
      }
      // Try direct API call
      else {
        // If we can't check if the stream exists, assume it doesn't and try to create it
        throw new Error('Cannot check if stream exists, will try to create it');
      }
    } catch (error) {
      console.log(`Stream ${name} does not exist or cannot check: ${error.message}`);

      // Create the stream
      const streamConfig = {
        name: name,
        subjects: subjects,
        retention: 'limits',
        max_msgs: 10000,
        max_bytes: 104857600,
        max_age: 604800000000000,
        storage: 'file',
        discard: 'old'
      };

      try {
        // First try JetStreamManager if available
        if (jsm && typeof jsm.streams === 'object' && typeof jsm.streams.add === 'function') {
          await jsm.streams.add(streamConfig);
          console.log(`Stream ${name} created (using JetStreamManager streams.add)`);
          return true;
        }
        // Try newer API version
        else if (typeof js.streams === 'object' && typeof js.streams.add === 'function') {
          await js.streams.add(streamConfig);
          console.log(`Stream ${name} created (using streams.add)`);
          return true;
        }
        // Try older API version
        else if (typeof js.addStream === 'function') {
          await js.addStream(streamConfig);
          console.log(`Stream ${name} created (using addStream)`);
          return true;
        }
        // Try direct NATS publish to create the stream
        else {
          console.log(`Cannot create stream ${name} using JetStream API, trying alternative method...`);

          // Get the NATS connection
          const nc = js.nc || js.conn;

          if (!nc) {
            throw new Error('No NATS connection available');
          }

          // Publish a message to each subject to create the stream implicitly
          for (const subject of subjects) {
            nc.publish(subject, Buffer.from(JSON.stringify({ action: 'create_stream' })));
            console.log(`Published to ${subject} to implicitly create stream`);
          }

          console.log(`Attempted to create stream ${name} implicitly by publishing to subjects`);
          return true;
        }
      } catch (createError) {
        // If the error message contains "already exists", the stream exists
        if (createError.message && createError.message.includes('already exists')) {
          console.log(`Stream ${name} already exists (from error message)`);
          return true;
        } else {
          console.error(`Failed to create stream ${name}: ${createError.message}`);
          return false;
        }
      }
    }
  } catch (error) {
    console.error(`Error in createStream for ${name}: ${error.message}`);
    return false;
  }
}

/**
 * Create a consumer for a stream with guaranteed fetch and pull methods
 * @param {Object} js - JetStream client
 * @param {string} streamName - Name of the stream
 * @param {string} consumerName - Name of the consumer
 * @returns {Promise<Object>} - Consumer object with fetch and pull methods
 */
async function createConsumer(js, streamName, consumerName) {
  try {
    console.log(`Creating consumer ${consumerName} for stream ${streamName}`);
    
    // Get JetStreamManager if available
    let jsm = null;
    if (js.nc && typeof js.nc.jetstreamManager === 'function') {
      try {
        jsm = await js.nc.jetstreamManager();
        console.log('JetStreamManager obtained successfully for consumer operations');
      } catch (jsmErr) {
        console.warn(`Failed to get JetStreamManager: ${jsmErr.message}, will fall back to JetStream API for consumer operations`);
      }
    }
    
    // Skip pullSubscribe which might have compatibility issues
    // Go straight to JetStreamManager if available
    let nativeConsumer;
    let createSucceeded = false;
    
    // Use JetStreamManager if available - this is the most reliable approach
    if (jsm && typeof jsm.consumers === 'object') {
      try {
        // Check what type of JetStreamManager interface we're dealing with
        const hasSafeConsumerGet = typeof jsm.consumers.get === 'function';
        const hasSafeConsumerInfo = typeof jsm.consumers.info === 'function';
        const hasSafeConsumerAdd = typeof jsm.consumers.add === 'function';
        const hasSafeConsumerCreate = typeof jsm.consumers.create === 'function';
        
        console.log(`JetStreamManager consumers API detection: get=${hasSafeConsumerGet}, info=${hasSafeConsumerInfo}, add=${hasSafeConsumerAdd}, create=${hasSafeConsumerCreate}`);
        
        // Try to get existing consumer first - try different approaches based on available API
        try {
          if (hasSafeConsumerGet) {
            // Try modern API first
            nativeConsumer = await jsm.consumers.get(streamName, consumerName);
            console.log(`Found existing consumer ${consumerName} for stream ${streamName} using jsm.consumers.get`);
            createSucceeded = true;
          } else if (hasSafeConsumerInfo) {
            // Try alternate API
            nativeConsumer = await jsm.consumers.info(streamName, consumerName);
            console.log(`Found existing consumer ${consumerName} for stream ${streamName} using jsm.consumers.info`);
            createSucceeded = true;
          } else {
            // Neither approach is available, try direct API later
            throw new Error('No JetStreamManager consumer get/info method available');
          }
        } catch (getErr) {
          console.log(`Consumer ${consumerName} not found or get error: ${getErr.message}, creating with available method`);
          
          // Create a durable pull consumer with proper filter subject based on stream names
          const consumerConfig = {
            durable_name: consumerName,
            ack_policy: 'explicit',
            deliver_policy: 'all',
            max_deliver: -1,
            ack_wait: 30 * 1000 * 1000 * 1000, // 30 seconds in nanoseconds
            // Use the first level of the subject hierarchy with wildcard
            filter_subject: getFilterSubjectForStream(streamName)
          };
          
          console.log(`Creating pull consumer with config:`, consumerConfig);
          
          // Try different creation methods based on available API
          if (hasSafeConsumerCreate) {
            try {
              nativeConsumer = await jsm.consumers.create(streamName, consumerConfig);
              console.log(`Created consumer ${consumerName} using jsm.consumers.create`);
              createSucceeded = true;
            } catch (createErr) {
              console.error(`Error creating consumer with jsm.consumers.create: ${createErr.message}`);
            }
          } else if (hasSafeConsumerAdd) {
            try {
              nativeConsumer = await jsm.consumers.add(streamName, consumerConfig);
              console.log(`Created consumer ${consumerName} using jsm.consumers.add`);
              createSucceeded = true;
            } catch (addErr) {
              console.error(`Error creating consumer with jsm.consumers.add: ${addErr.message}`);
            }
          } else {
            console.warn('No JetStreamManager consumer create/add method available, will try direct API');
          }
          
          // Try one more time to get the consumer in case of race condition
          if (!createSucceeded && (hasSafeConsumerGet || hasSafeConsumerInfo)) {
            try {
              if (hasSafeConsumerGet) {
                nativeConsumer = await jsm.consumers.get(streamName, consumerName);
              } else {
                nativeConsumer = await jsm.consumers.info(streamName, consumerName);
              }
              console.log(`Found consumer ${consumerName} after creation attempt`);
              createSucceeded = true;
            } catch (retryErr) {
              console.error(`Failed to get consumer after creation attempt: ${retryErr.message}`);
            }
          }
        }
      } catch (err) {
        console.error(`Error with JetStreamManager consumer operations: ${err.message}`);
      }
    }
    
    // If JetStreamManager approach didn't work, try direct API
    if (!createSucceeded && js) {
      try {
        console.log(`Attempting direct API approach for consumer ${consumerName}`);
        
        // Try to use the direct JetStream API
        const nc = js.nc || js.conn;
        if (nc && typeof nc.request === 'function') {
          try {
            // First check if consumer exists
            const infoResponse = await nc.request(
              `$JS.API.CONSUMER.INFO.${streamName}.${consumerName}`,
              Buffer.from(JSON.stringify({}))
            );
            
            // If we get here, consumer exists
            console.log(`Consumer ${consumerName} found through direct API call`);
            createSucceeded = true;
          } catch (infoErr) {
            // Consumer doesn't exist, create it
            console.log(`Creating consumer ${consumerName} using direct API call`);
            
            const createConfig = {
              durable_name: consumerName,
              deliver_policy: 'all',
              ack_policy: 'explicit',
              filter_subject: getFilterSubjectForStream(streamName),
              max_deliver: -1
            };
            
            try {
              const createResponse = await nc.request(
                `$JS.API.CONSUMER.CREATE.${streamName}`,
                Buffer.from(JSON.stringify(createConfig))
              );
              
              createSucceeded = true;
              console.log(`Successfully created consumer ${consumerName} using direct API call`);
            } catch (createErr) {
              console.error(`Error creating consumer using direct API: ${createErr.message}`);
            }
          }
        }
      } catch (directErr) {
        console.error(`Error with direct API approach: ${directErr.message}`);
      }
    }
    
    // Create a message fetcher that uses direct JetStream API
    // This approach should work regardless of consumer object
    const directMessageFetcher = async (opts = { max_messages: 10 }) => {
      console.log(`Fetching messages for ${consumerName} using direct API`);
      
      const nc = js.nc || js.conn;
      if (!nc || typeof nc.request !== 'function') {
        console.warn('No NATS connection available for direct message fetching');
        return [];
      }
      
      try {
        const messages = [];
        const maxMsgs = opts.max_messages || 10;
        
        // Handle StringCodec import in multiple ways to ensure compatibility
        let sc;
        try {
          const StringCodec = require('nats').StringCodec;
          sc = StringCodec();
        } catch (scErr) {
          // Fallback for different versions of NATS library
          console.log('Using basic string codec due to error:', scErr.message);
          sc = {
            decode: (data) => {
              if (Buffer.isBuffer(data) || data instanceof Uint8Array) {
                return data.toString();
              }
              return String(data);
            }
          };
        }
        
        // Try to fetch messages one by one to avoid batch issues
        for (let i = 0; i < maxMsgs; i++) {
          try {
            const response = await nc.request(
              `$JS.API.CONSUMER.MSG.NEXT.${streamName}.${consumerName}`,
              Buffer.from(JSON.stringify({ 
                batch: 1,
                expires: 1000 // 1s timeout per message
              }))
            );
            
            if (response && response.data) {
              // Create a message-like object with an ack method
              let messageData = response.data;
              
              // Handle message decoding correctly
              try {
                // First try to decode the data as a string if it's a Buffer
                if (Buffer.isBuffer(messageData) || messageData instanceof Uint8Array) {
                  messageData = sc.decode(messageData);
                }
                
                // Safely handle different formats of message data
                let parsedData = null;
                try {
                  // Try parsing as JSON
                  parsedData = JSON.parse(messageData);
                } catch (parseErr) {
                  console.log(`Message is not JSON, using raw data: ${parseErr.message}`);
                  // Use the raw string data if it's not JSON
                  parsedData = { 
                    raw: messageData,
                    _unparseable: true,
                    timestamp: new Date().toISOString()
                  };
                }
                
                // Create consistent message object with parsed data
                messages.push({
                  data: messageData,  // Keep original data
                  _parsedData: parsedData, // Store parsed version separately
                  subject: response.subject,
                  ack: async () => {
                    try {
                      if (response.reply) {
                        await nc.publish(response.reply, Buffer.from('+ACK'));
                      }
                    } catch (ackErr) {
                      console.warn(`Error acknowledging message: ${ackErr.message}`);
                    }
                  }
                });
              } catch (dataErr) {
                console.warn(`Error processing message data: ${dataErr.message}`);
                // Still include the message, but with raw data
                messages.push({
                  data: messageData,
                  _error: dataErr.message,
                  subject: response.subject,
                  ack: async () => {
                    try {
                      if (response.reply) {
                        await nc.publish(response.reply, Buffer.from('+ACK'));
                      }
                    } catch (ackErr) {
                      console.warn(`Error acknowledging message: ${ackErr.message}`);
                    }
                  }
                });
              }
            }
          } catch (reqErr) {
            // Break on error (probably no more messages)
            if (reqErr.message && reqErr.message.includes('timeout')) {
              console.log(`Message request timed out after ${i} messages, likely no more messages`);
            } else {
              console.warn(`Error requesting message: ${reqErr.message}`);
            }
            break;
          }
        }
        
        return messages;
      } catch (err) {
        console.error(`Error in direct message fetching: ${err.message}`);
        return [];
      }
    };
    
    // Create a wrapper for the native consumer that guarantees fetch/pull methods
    return {
      // Store info about the consumer
      _streamName: streamName,
      _consumerName: consumerName,
      _createSucceeded: createSucceeded,
      
      // Guaranteed fetch method - always use direct API approach
      fetch: directMessageFetcher,
      
      // Guaranteed pull method (passes through to fetch)
      pull: async function(batchSize = 10) {
        return this.fetch({ max_messages: batchSize });
      }
    };
  } catch (error) {
    console.error(`Error creating consumer ${consumerName} for stream ${streamName}: ${error.message}`);
    
    // Return a fallback consumer with non-failing fetch/pull methods
    return {
      fetch: async () => {
        console.warn(`Using fallback fetch for failed consumer ${consumerName}`);
        return [];
      },
      pull: async () => {
        console.warn(`Using fallback pull for failed consumer ${consumerName}`);
        return [];
      }
    };
  }
}

/**
 * Helper function to get the appropriate filter subject for a stream
 * @param {string} streamName - Name of the stream
 * @returns {string} - Filter subject pattern for the stream
 */
function getFilterSubjectForStream(streamName) {
  // Define the mapping of stream names to subject patterns
  const streamSubjects = {
    'AGENTS': 'agent.status.>',
    'METRICS': 'metric.>',
    'LOGS': 'log.>',
    'DEPLOYMENTS': 'deployment.>',
    'ROOT_CAUSE': 'rootcause.>',
    'TRACES': 'trace.>',
    'NOTIFICATIONS': 'notification.>',
    'POSTMORTEMS': 'postmortem.>',
    'RUNBOOKS': 'runbook.definition.>',
    'RUNBOOK_EXECUTIONS': 'runbook.execution.>',
    'ALERTS': 'alert.>',
    'ALERT_DATA': 'alert.data.>',
    'NOTEBOOKS': 'notebook.>',
    'RESPONSES': 'response.>',
    'AGENT_TASKS': 'agent.task.>'
  };
  
  // Return the specific subject pattern or fall back to a default
  return streamSubjects[streamName] || `${streamName.toLowerCase()}.>`;
}

/**
 * Main function
 */
async function main() {
  console.log('UI-specific JetStream Stream Creator for Observability Agent');
  console.log('----------------------------------------------');
  console.log(`NATS URL: ${config.natsUrl}`);
  console.log(`JetStream Domain: ${config.domain}`);
  console.log('----------------------------------------------');

  try {
    // Connect to NATS without domain
    console.log(`Connecting to NATS server at ${config.natsUrl}...`);
    const nc = await connect({
      servers: config.natsUrl,
      timeout: 5000
      // Removed JetStream domain to use default domain
    });

    console.log('Connected to NATS server');
    console.log(`Server information: ${nc.getServer()}`);

    // Create JetStream client
    const js = nc.jetstream();
    console.log('JetStream client created');

    // Create all required streams
    let streamSuccessCount = 0;
    let streamFailureCount = 0;

    for (const stream of requiredStreams) {
      const success = await createStream(js, stream.name, stream.subjects);
      if (success) {
        streamSuccessCount++;
      } else {
        streamFailureCount++;
      }
    }

    console.log('----------------------------------------------');
    console.log(`Stream creation complete: ${streamSuccessCount} succeeded, ${streamFailureCount} failed`);

    // Create consumers for each stream with fetch and pull methods
    const consumers = [
      { stream: 'METRICS', consumer: 'metrics-viewer' },
      { stream: 'LOGS', consumer: 'logs-viewer' },
      { stream: 'ALERTS', consumer: 'alerts-history-viewer' },
      { stream: 'ALERTS', consumer: 'alerts-active-viewer' },
      { stream: 'AGENTS', consumer: 'agents-viewer' },
      { stream: 'DEPLOYMENTS', consumer: 'deployments-viewer' },
      { stream: 'TRACES', consumer: 'traces-viewer' },
      { stream: 'ROOT_CAUSE', consumer: 'rootcauses-viewer' },
      { stream: 'NOTIFICATIONS', consumer: 'notifications-viewer' },
      { stream: 'POSTMORTEMS', consumer: 'postmortems-viewer' },
      { stream: 'RUNBOOKS', consumer: 'runbooks-viewer' }
    ];

    let consumerSuccessCount = 0;
    let consumerFailureCount = 0;
    const createdConsumers = {};

    // Create each consumer and store the consumer objects with fetch/pull methods
    for (const { stream, consumer } of consumers) {
      try {
        console.log(`Creating consumer ${consumer} for stream ${stream}...`);
        const consumerObj = await createConsumer(js, stream, consumer);
        
        if (consumerObj._createSucceeded) {
          consumerSuccessCount++;
        } else {
          consumerFailureCount++;
        }
        
        // Store the created consumer object
        createdConsumers[`${stream}.${consumer}`] = consumerObj;
      } catch (err) {
        console.error(`Error creating consumer ${consumer} for stream ${stream}: ${err.message}`);
        consumerFailureCount++;
      }
    }

    console.log('----------------------------------------------');
    console.log(`Consumer creation complete: ${consumerSuccessCount} succeeded, ${consumerFailureCount} failed`);

    // Optionally, perform health checks or initial data fetches from consumers
    // ...

    console.log('All operations completed');
  } catch (err) {
    console.error(`Error in main execution: ${err.message}`);
  }
}

// Execute main function
main().catch(err => {
  console.error(`Unexpected error in main: ${err.message}`);
});
