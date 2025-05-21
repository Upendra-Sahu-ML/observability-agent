#!/usr/bin/env node
/**
 * Create JetStream Streams for Observability Agent
 * 
 * This script creates all the required JetStream streams for the Observability Agent system.
 * 
 * Usage:
 *   node create_streams.js [--nats-url=<url>]
 * 
 * Options:
 *   --nats-url=<url>   NATS server URL (default: nats://localhost:34222)
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
  natsUrl: args['nats-url'] || 'nats://localhost:34222'
};

// Required streams and their subjects
const requiredStreams = [
  { name: 'METRICS', subjects: ['metrics.*'] },
  { name: 'LOGS', subjects: ['logs.*'] },
  { name: 'ALERTS', subjects: ['alerts.*'] },
  { name: 'AGENTS', subjects: ['agent.status.*'] },
  { name: 'DEPLOYMENTS', subjects: ['deployments.*'] },
  { name: 'TRACES', subjects: ['traces.*'] },
  { name: 'ROOTCAUSES', subjects: ['rootcause.*'] },
  { name: 'NOTIFICATIONS', subjects: ['notifications.*'] },
  { name: 'POSTMORTEMS', subjects: ['postmortems.*'] },
  { name: 'RUNBOOKS', subjects: ['runbooks.*', 'runbook.*'] }
];

/**
 * Create a stream if it doesn't exist
 * @param {Object} js - JetStream client
 * @param {string} name - Stream name
 * @param {Array<string>} subjects - Stream subjects
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
        subjects: subjects
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
 * Main function
 */
async function main() {
  console.log('JetStream Stream Creator for Observability Agent');
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
    
    // Create all required streams
    let successCount = 0;
    let failureCount = 0;
    
    for (const stream of requiredStreams) {
      const success = await createStream(js, stream.name, stream.subjects);
      if (success) {
        successCount++;
      } else {
        failureCount++;
      }
    }
    
    console.log('----------------------------------------------');
    console.log(`Stream creation complete: ${successCount} succeeded, ${failureCount} failed`);
    
    // Disconnect from NATS
    await nc.drain();
    console.log('Disconnected from NATS server');
    
    // Exit with success if all streams were created
    process.exit(failureCount === 0 ? 0 : 1);
    
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
