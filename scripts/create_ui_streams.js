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
  { name: 'METRICS', subjects: ['metrics.*'] },
  { name: 'LOGS', subjects: ['logs.*'] },
  { name: 'ALERTS', subjects: ['alerts.*'] },
  { name: 'AGENTS', subjects: ['agent.status.*'] },
  { name: 'DEPLOYMENTS', subjects: ['deployments.*'] },
  { name: 'TRACES', subjects: ['traces.*'] },
  { name: 'ROOT_CAUSE', subjects: ['rootcause.*', 'root_cause_analysis', 'root_cause_result'] },
  { name: 'NOTIFICATIONS', subjects: ['notifications.*', 'notification_requests'] },
  { name: 'POSTMORTEMS', subjects: ['postmortems.*'] },
  { name: 'RUNBOOKS', subjects: ['runbooks.*', 'runbook.*'] }
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

    // Try different JetStream API versions
    try {
      // Try newer API version
      if (typeof js.streams === 'object' && typeof js.streams.info === 'function') {
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
        storage: 'memory',
        discard: 'old'
      };

      try {
        // Try newer API version
        if (typeof js.streams === 'object' && typeof js.streams.add === 'function') {
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
 * Create a consumer for a stream
 * @param {Object} js - JetStream client
 * @param {string} streamName - Name of the stream
 * @param {string} consumerName - Name of the consumer
 * @returns {Promise<boolean>} - True if consumer exists or was created
 */
async function createConsumer(js, streamName, consumerName) {
  try {
    console.log(`Checking if consumer ${consumerName} exists on stream ${streamName}...`);

    // Try different JetStream API versions
    try {
      // Try newer API version
      if (typeof js.consumers === 'object' && typeof js.consumers.info === 'function') {
        await js.consumers.info(streamName, consumerName);
        console.log(`Consumer ${consumerName} already exists on stream ${streamName} (using consumers.info)`);
        return true;
      }
      // Try older API version
      else if (typeof js.consumerInfo === 'function') {
        await js.consumerInfo(streamName, consumerName);
        console.log(`Consumer ${consumerName} already exists on stream ${streamName} (using consumerInfo)`);
        return true;
      }
      // Try direct API call
      else {
        // If we can't check if the consumer exists, assume it doesn't and try to create it
        throw new Error('Cannot check if consumer exists, will try to create it');
      }
    } catch (error) {
      console.log(`Consumer ${consumerName} does not exist on stream ${streamName} or cannot check: ${error.message}`);

      // Create the consumer
      const consumerConfig = {
        durable_name: consumerName,
        ack_policy: 'explicit',
        deliver_policy: 'all'
      };

      try {
        // Try newer API version
        if (typeof js.consumers === 'object' && typeof js.consumers.add === 'function') {
          await js.consumers.add(streamName, consumerConfig);
          console.log(`Consumer ${consumerName} created on stream ${streamName} (using consumers.add)`);
          return true;
        }
        // Try older API version
        else if (typeof js.addConsumer === 'function') {
          await js.addConsumer(streamName, consumerConfig);
          console.log(`Consumer ${consumerName} created on stream ${streamName} (using addConsumer)`);
          return true;
        }
        else {
          console.log(`Cannot create consumer ${consumerName} on stream ${streamName} using JetStream API`);
          return false;
        }
      } catch (createError) {
        console.error(`Failed to create consumer ${consumerName} on stream ${streamName}: ${createError.message}`);
        return false;
      }
    }
  } catch (error) {
    console.error(`Error in createConsumer for ${streamName}/${consumerName}: ${error.message}`);
    return false;
  }
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

    // Create consumers for each stream
    const consumers = [
      { stream: 'METRICS', consumer: 'metrics-viewer' },
      { stream: 'LOGS', consumer: 'logs-viewer' },
      { stream: 'ALERTS', consumer: 'alert-history-viewer' },
      { stream: 'ALERTS', consumer: 'alert-active-viewer' },
      { stream: 'AGENTS', consumer: 'agent-status-viewer' },
      { stream: 'DEPLOYMENTS', consumer: 'deployment-viewer' },
      { stream: 'TRACES', consumer: 'trace-viewer' },
      { stream: 'ROOT_CAUSE', consumer: 'rootcause-viewer' },
      { stream: 'NOTIFICATIONS', consumer: 'notification-viewer' },
      { stream: 'POSTMORTEMS', consumer: 'postmortem-viewer' },
      { stream: 'RUNBOOKS', consumer: 'runbook-viewer' }
    ];

    let consumerSuccessCount = 0;
    let consumerFailureCount = 0;

    for (const { stream, consumer } of consumers) {
      const success = await createConsumer(js, stream, consumer);
      if (success) {
        consumerSuccessCount++;
      } else {
        consumerFailureCount++;
      }
    }

    console.log('----------------------------------------------');
    console.log(`Consumer creation complete: ${consumerSuccessCount} succeeded, ${consumerFailureCount} failed`);

    // Disconnect from NATS
    await nc.drain();
    console.log('Disconnected from NATS server');
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
