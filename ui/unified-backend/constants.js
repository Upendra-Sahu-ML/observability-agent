/**
 * Constants for the UI backend
 * This file provides centralized configuration values used throughout the UI backend
 */

// Stream name constants to ensure consistency in JetStream usage
// These names match exactly what's in the NATS server
const STREAM_NAMES = {
  AGENTS: 'AGENTS',
  METRICS: 'METRICS',
  LOGS: 'LOGS',
  DEPLOYMENTS: 'DEPLOYMENTS',
  ROOT_CAUSES: 'ROOT_CAUSE',  // Note: Actual stream name is ROOT_CAUSE, not ROOT_CAUSES
  TRACES: 'TRACES',
  NOTIFICATIONS: 'NOTIFICATIONS',
  POSTMORTEMS: 'POSTMORTEMS',
  RUNBOOKS: 'RUNBOOKS',
  ALERTS: 'ALERTS',
  ALERT_DATA: 'ALERT_DATA',
  NOTEBOOKS: 'NOTEBOOKS',
  RESPONSES: 'RESPONSES',
  AGENT_TASKS: 'AGENT_TASKS',
  RUNBOOK_EXECUTIONS: 'RUNBOOK_EXECUTIONS'
};

// Consumer name constants to ensure consistency across code
// These need to match the names that the UI backend is using when querying NATS
const CONSUMER_NAMES = {
  AGENTS: 'agents-viewer',
  METRICS: 'metrics-viewer',
  LOGS: 'logs-viewer',
  DEPLOYMENTS: 'deployments-viewer',
  ROOT_CAUSES: 'rootcauses-viewer',
  TRACES: 'traces-viewer',           // Updated from 'trace-viewer' based on getTracingData function
  NOTIFICATIONS: 'notifications-viewer', // Updated from 'notification-viewer'
  POSTMORTEMS: 'postmortems-viewer', // Updated from 'postmortem-viewer'
  RUNBOOKS: 'runbook-viewer',         // Keep consistent with existing usage
  ALERTS_HISTORY: 'alerts-history-viewer',
  ALERTS_ACTIVE: 'alerts-active-viewer'
};

// Define stream subject patterns for consumers to use consistent filtering
// These patterns MUST match the Helm NATS configuration exactly
const STREAM_SUBJECTS = {
  AGENTS: 'agent.status.>',
  METRICS: 'metrics.>',              // Fixed: was 'metric.>'
  LOGS: 'logs.>',                    // Fixed: was 'log.>'
  DEPLOYMENTS: 'deployments.>',
  ROOT_CAUSES: 'rootcause.>',
  TRACES: 'traces.>',                // Fixed: was 'trace.>'
  NOTIFICATIONS: 'notifications.>',   // Fixed: was 'notification.>'
  POSTMORTEMS: 'postmortems.>',      // Fixed: was 'postmortem.>'
  RUNBOOKS: 'runbook.definition.>',
  RUNBOOK_EXECUTIONS: 'runbook.execution.>',
  ALERTS: 'alerts.>',                // Fixed: was 'alert.>'
  ALERT_DATA: 'alert.data.>',
  NOTEBOOKS: 'notebooks.>',          // Fixed: was 'notebook.>'
  RESPONSES: 'responses.>',          // Fixed: was 'response.>'
  AGENT_TASKS: 'agent.tasks.>'       // Fixed: was 'agent.task.>'
};

/**
 * Check if a stream exists in NATS
 * @param {object} js - JetStream instance
 * @param {string} streamName - Name of the stream to check
 * @returns {Promise<boolean>} - True if stream exists, false otherwise
 */
async function checkStreamExists(js, streamName) {
  try {
    // Get JetStreamManager from the wrapper if available
    const jsm = js._jsm || null;

    // Only use JetStreamManager for checking if a stream exists
    if (jsm && typeof jsm.streams === 'object' && typeof jsm.streams.info === 'function') {
      console.log(`Using JetStreamManager to check if stream ${streamName} exists`);
      try {
        await jsm.streams.info(streamName);
        return true;
      } catch (error) {
        if (error.code === '404') {
          return false;
        }
        throw error;
      }
    }

    // If JetStreamManager is not available, return false
    console.warn(`JetStreamManager not available to check for stream ${streamName}, returning false`);
    return false;
  } catch (error) {
    console.warn(`Error checking if stream ${streamName} exists: ${error.message}`);
    return false;
  }
}

/**
 * Create a consumer for a stream
 * @param {object} jsm - JetStream Manager instance
 * @param {object} js - JetStream instance
 * @param {string} streamName - Name of the stream
 * @param {string} consumerName - Name of the consumer
 * @returns {Promise<object>} - Consumer object with guaranteed fetch and pull methods
 */
async function createConsumer(jsm, js, streamName, consumerName) {
  try {
    console.log(`Creating consumer ${consumerName} for stream ${streamName}`);

    // Skip pullSubscribe which seems to be having compatibility issues
    // Go straight to JetStreamManager if available
    let nativeConsumer;
    let createSucceeded = false;

    // Use JetStreamManager if available - this is the most reliable approach
    if (jsm && typeof jsm.consumers === 'object') {
      try {
        // Try to get existing consumer first
        try {
          nativeConsumer = await jsm.consumers.get(streamName, consumerName);
          console.log(`Found existing consumer ${consumerName} for stream ${streamName}`);
          createSucceeded = true;
        } catch (getErr) {
          console.log(`Consumer ${consumerName} not found, creating with JetStreamManager`);

          // Get the appropriate filter subject for this stream
          const streamKey = Object.keys(STREAM_NAMES).find(key => STREAM_NAMES[key] === streamName);
          const filterSubject = streamKey && STREAM_SUBJECTS[streamKey] ?
                               STREAM_SUBJECTS[streamKey] :
                               `${streamName.toLowerCase()}.>`;

          // Create a durable pull consumer
          const consumerConfig = {
            durable_name: consumerName,
            ack_policy: 'explicit',
            deliver_policy: 'all',
            max_deliver: -1,
            ack_wait: 30 * 1000 * 1000 * 1000, // 30 seconds in nanoseconds
            filter_subject: filterSubject
          };

          console.log(`Creating pull consumer with config:`, consumerConfig);

          // Create consumer using a safer approach
          try {
            // First try with the create method (newer versions might use this)
            if (typeof jsm.consumers.create === 'function') {
              nativeConsumer = await jsm.consumers.create(streamName, consumerConfig);
              createSucceeded = true;
            }
            // Fall back to add if create isn't available
            else if (typeof jsm.consumers.add === 'function') {
              nativeConsumer = await jsm.consumers.add(streamName, consumerConfig);
              createSucceeded = true;
            }
          } catch (createErr) {
            console.error(`Error creating consumer: ${createErr.message}`);
            // Try to get it one more time in case of race condition
            try {
              nativeConsumer = await jsm.consumers.get(streamName, consumerName);
              createSucceeded = true;
            } catch (retryErr) {
              console.error(`Failed to create or get consumer ${consumerName}: ${retryErr.message}`);
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
        if (js._nc && typeof js._nc.request === 'function') {
          try {
            // First check if consumer exists
            const infoResponse = await js._nc.request(
              `$JS.API.CONSUMER.INFO.${streamName}.${consumerName}`,
              Buffer.from(JSON.stringify({}))
            );

            // If we get here, consumer exists
            console.log(`Consumer ${consumerName} found through direct API call`);
            createSucceeded = true;
          } catch (infoErr) {
            // Consumer doesn't exist, create it
            console.log(`Creating consumer ${consumerName} using direct API call`);

            // Get the appropriate filter subject for this stream
            const streamKey = Object.keys(STREAM_NAMES).find(key => STREAM_NAMES[key] === streamName);
            const filterSubject = streamKey && STREAM_SUBJECTS[streamKey] ?
                                 STREAM_SUBJECTS[streamKey] :
                                 `${streamName.toLowerCase()}.>`;

            const createConfig = {
              durable_name: consumerName,
              deliver_policy: 'all',
              ack_policy: 'explicit',
              filter_subject: filterSubject,
              max_deliver: -1
            };

            try {
              const createResponse = await js._nc.request(
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

      if (!js || !js._nc || typeof js._nc.request !== 'function') {
        console.warn('No NATS connection available for direct message fetching');
        return [];
      }

      try {
        const messages = [];
        const maxMsgs = opts.max_messages || 10;
        const StringCodec = require('nats').StringCodec;
        const sc = StringCodec();

        // Try to fetch messages one by one to avoid batch issues
        for (let i = 0; i < maxMsgs; i++) {
          try {
            const response = await js._nc.request(
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
                        await js._nc.publish(response.reply, Buffer.from('+ACK'));
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
                        await js._nc.publish(response.reply, Buffer.from('+ACK'));
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

module.exports = {
  STREAM_NAMES,
  CONSUMER_NAMES,
  STREAM_SUBJECTS,
  checkStreamExists,
  createConsumer
};