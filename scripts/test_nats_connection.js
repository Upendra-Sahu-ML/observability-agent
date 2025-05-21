#!/usr/bin/env node
/**
 * Test NATS Connection and Streams
 * 
 * This script tests the connection to NATS and lists all streams and consumers.
 * 
 * Usage:
 *   node test_nats_connection.js [--nats-url=<url>] [--domain=<domain>]
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

/**
 * List all streams
 * @param {Object} js - JetStream client
 */
async function listStreams(js) {
  console.log('Listing all streams:');
  console.log('-------------------');
  
  try {
    let streams;
    
    // Try different JetStream API versions
    if (typeof js.streams === 'object' && typeof js.streams.list === 'function') {
      console.log('Using newer JetStream API (streams.list)');
      streams = await js.streams.list().next();
    } else if (typeof js.streams === 'function') {
      console.log('Using older JetStream API (streams)');
      streams = await js.streams().next();
    } else {
      console.warn('JetStream API does not support listing streams');
      return;
    }
    
    if (!streams) {
      console.log('No streams found');
      return;
    }
    
    console.log(`Found ${streams.length} streams:`);
    
    for (const stream of streams) {
      console.log(`- ${stream.config.name}`);
      console.log(`  Subjects: ${stream.config.subjects.join(', ')}`);
      console.log(`  Messages: ${stream.state.messages}`);
      console.log(`  Bytes: ${stream.state.bytes}`);
      console.log(`  Consumers: ${stream.state.consumer_count}`);
      console.log('-------------------');
    }
  } catch (error) {
    console.error(`Error listing streams: ${error.message}`);
  }
}

/**
 * List consumers for a stream
 * @param {Object} js - JetStream client
 * @param {string} streamName - Name of the stream
 */
async function listConsumers(js, streamName) {
  console.log(`Listing consumers for stream ${streamName}:`);
  console.log('-------------------');
  
  try {
    let consumers;
    
    // Try different JetStream API versions
    if (typeof js.consumers === 'object' && typeof js.consumers.list === 'function') {
      console.log('Using newer JetStream API (consumers.list)');
      consumers = await js.consumers.list(streamName).next();
    } else if (typeof js.consumers === 'function') {
      console.log('Using older JetStream API (consumers)');
      consumers = await js.consumers(streamName).next();
    } else {
      console.warn('JetStream API does not support listing consumers');
      return;
    }
    
    if (!consumers) {
      console.log(`No consumers found for stream ${streamName}`);
      return;
    }
    
    console.log(`Found ${consumers.length} consumers for stream ${streamName}:`);
    
    for (const consumer of consumers) {
      console.log(`- ${consumer.name}`);
      console.log(`  Delivered: ${consumer.delivered.consumer_seq}`);
      console.log(`  Ack Pending: ${consumer.num_pending}`);
      console.log(`  Redelivered: ${consumer.num_redelivered}`);
      console.log('-------------------');
    }
  } catch (error) {
    console.error(`Error listing consumers for stream ${streamName}: ${error.message}`);
  }
}

/**
 * Main function
 */
async function main() {
  console.log('NATS Connection and Stream Test');
  console.log('----------------------------------------------');
  console.log(`NATS URL: ${config.natsUrl}`);
  console.log(`JetStream Domain: ${config.domain}`);
  console.log('----------------------------------------------');
  
  try {
    // Connect to NATS with domain
    console.log(`Connecting to NATS server at ${config.natsUrl} with domain ${config.domain}...`);
    const nc = await connect({
      servers: config.natsUrl,
      timeout: 5000,
      jetstreamDomain: config.domain
    });
    
    console.log('Connected to NATS server');
    console.log(`Server information: ${nc.getServer()}`);
    console.log(`Server ID: ${nc.info.server_id}`);
    console.log(`Server version: ${nc.info.version}`);
    console.log(`Server protocol: ${nc.info.proto}`);
    console.log(`JetStream available: ${nc.info.jetstream ? 'Yes' : 'No'}`);
    console.log('----------------------------------------------');
    
    // Create JetStream client
    const js = nc.jetstream();
    console.log('JetStream client created');
    
    // List all streams
    await listStreams(js);
    
    // List consumers for each stream
    const requiredStreams = [
      'METRICS', 'LOGS', 'ALERTS', 'AGENTS', 'DEPLOYMENTS', 
      'TRACES', 'ROOTCAUSES', 'NOTIFICATIONS', 'POSTMORTEMS', 'RUNBOOKS'
    ];
    
    for (const streamName of requiredStreams) {
      try {
        // Check if stream exists
        let streamExists = false;
        
        try {
          if (typeof js.streams === 'object' && typeof js.streams.info === 'function') {
            await js.streams.info(streamName);
            streamExists = true;
          } else if (typeof js.streamInfo === 'function') {
            await js.streamInfo(streamName);
            streamExists = true;
          }
        } catch (error) {
          console.log(`Stream ${streamName} does not exist: ${error.message}`);
          continue;
        }
        
        if (streamExists) {
          await listConsumers(js, streamName);
        }
      } catch (error) {
        console.error(`Error processing stream ${streamName}: ${error.message}`);
      }
    }
    
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
