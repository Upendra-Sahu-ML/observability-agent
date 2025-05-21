#!/usr/bin/env node
/**
 * Fix NATS Streams for Observability Agent
 *
 * This script creates missing streams and adds missing subjects to existing streams
 * to fix the CrashLoopBackOff issues with metric-agent and root-cause-agent.
 *
 * Usage:
 *   node fix_nats_streams.js [--nats-url=<url>]
 *
 * Options:
 *   --nats-url=<url>   NATS server URL (default: nats://localhost:4222)
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
  natsUrl: args['nats-url'] || 'nats://localhost:4222'
};

/**
 * Create a stream if it doesn't exist
 * @param {Object} js - JetStream client
 * @param {string} name - Name of the stream
 * @param {Array<string>} subjects - Subjects for the stream
 * @returns {Promise<boolean>} - True if stream exists or was created
 */
async function createStream(js, name, subjects) {
  try {
    // Check if stream exists
    try {
      await js.stream_info(name);
      console.log(`Stream ${name} already exists`);
      return true;
    } catch (error) {
      // Stream doesn't exist, create it
      console.log(`Stream ${name} does not exist, creating...`);

      try {
        // Create the stream
        await js.add_stream({
          name: name,
          subjects: subjects,
          retention: 'limits',
          max_msgs: 10000,
          max_bytes: 104857600,  // 100MB
          max_age: 604800000000000,  // 7 days in nanoseconds
          storage: 'memory',
          discard: 'old'
        });
        console.log(`Created stream ${name} with subjects: ${subjects.join(', ')}`);
        return true;
      } catch (createError) {
        console.error(`Failed to create stream ${name}: ${createError.message}`);
        return false;
      }
    }
  } catch (error) {
    console.error(`Error in createStream for ${name}: ${error.message}`);
    return false;
  }
}

/**
 * Update a stream to add new subjects
 * @param {Object} js - JetStream client
 * @param {string} name - Name of the stream
 * @param {Array<string>} newSubjects - New subjects to add
 * @returns {Promise<boolean>} - True if stream was updated
 */
async function updateStream(js, name, newSubjects) {
  try {
    // Get current stream info
    const streamInfo = await js.stream_info(name);
    const currentSubjects = streamInfo.config.subjects || [];

    // Check if all new subjects are already in the stream
    const missingSubjects = newSubjects.filter(subject => !currentSubjects.includes(subject));

    if (missingSubjects.length === 0) {
      console.log(`All subjects already exist in stream ${name}`);
      return true;
    }

    // Add new subjects to the stream
    const updatedSubjects = [...currentSubjects, ...missingSubjects];

    // Update the stream
    await js.update_stream({
      name: name,
      subjects: updatedSubjects
    });

    console.log(`Updated stream ${name} with new subjects: ${missingSubjects.join(', ')}`);
    return true;
  } catch (error) {
    console.error(`Error updating stream ${name}: ${error.message}`);
    return false;
  }
}

/**
 * Main function
 */
async function main() {
  console.log('NATS Stream Fixer for Observability Agent');
  console.log('----------------------------------------------');
  console.log(`NATS URL: ${config.natsUrl}`);
  console.log('----------------------------------------------');

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

    // Define all required streams with their subjects
    const requiredStreams = [
      {
        name: 'ALERTS',
        subjects: ['alerts', 'alerts.>']
      },
      {
        name: 'AGENT_TASKS',
        subjects: [
          'metric_agent', 'log_agent', 'deployment_agent', 'tracing_agent',
          'root_cause_agent', 'notification_agent', 'postmortem_agent', 'runbook_agent'
        ]
      },
      {
        name: 'RESPONSES',
        subjects: ['orchestrator_response']
      },
      {
        name: 'ALERT_DATA',
        subjects: ['alert_data_request', 'alert_data_response.*']
      },
      {
        name: 'ROOT_CAUSE',
        subjects: ['root_cause_analysis', 'root_cause_result', 'rootcause', 'rootcause.*']
      },
      {
        name: 'METRICS',
        subjects: ['metrics', 'metrics.*']
      },
      {
        name: 'LOGS',
        subjects: ['logs', 'logs.*']
      },
      {
        name: 'DEPLOYMENTS',
        subjects: ['deployments', 'deployments.*']
      },
      {
        name: 'TRACES',
        subjects: ['traces', 'traces.*']
      },
      {
        name: 'POSTMORTEMS',
        subjects: ['postmortems', 'postmortems.*']
      },
      {
        name: 'RUNBOOKS',
        subjects: ['runbooks', 'runbooks.*', 'runbook', 'runbook.data.*']
      },
      {
        name: 'RUNBOOK_EXECUTIONS',
        subjects: ['runbook.execute', 'runbook.status.*']
      },
      {
        name: 'NOTEBOOKS',
        subjects: ['notebooks', 'notebooks.*']
      },
      {
        name: 'NOTIFICATIONS',
        subjects: ['notification_requests', 'notifications', 'notifications.*']
      }
    ];

    // Get existing streams
    console.log('Getting existing streams...');
    const existingStreams = {};
    try {
      const streams = await js.streams.list().next();
      for (const stream of streams.streams) {
        existingStreams[stream.config.name] = stream.config.subjects;
        console.log(`Found existing stream: ${stream.config.name} with subjects: ${stream.config.subjects.join(', ')}`);
      }
    } catch (error) {
      console.error(`Error listing streams: ${error.message}`);
    }

    // Check for overlapping subjects
    console.log('\nChecking for overlapping subjects...');
    const subjectToStream = {};
    for (const [streamName, subjects] of Object.entries(existingStreams)) {
      for (const subject of subjects) {
        if (subjectToStream[subject]) {
          console.warn(`Subject ${subject} is used in multiple streams: ${subjectToStream[subject]} and ${streamName}`);
        } else {
          subjectToStream[subject] = streamName;
        }
      }
    }

    // Create or update streams
    console.log('\nCreating or updating streams...');
    for (const stream of requiredStreams) {
      if (existingStreams[stream.name]) {
        // Stream exists, update if needed
        await updateStream(js, stream.name, stream.subjects);
      } else {
        // Stream doesn't exist, create it
        await createStream(js, stream.name, stream.subjects);
      }
    }

    // Disconnect from NATS
    await nc.drain();
    console.log('Disconnected from NATS server');

    console.log('----------------------------------------------');
    console.log('NATS streams fixed successfully');
    console.log('----------------------------------------------');
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
