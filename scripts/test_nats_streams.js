#!/usr/bin/env node
/**
 * Script to test NATS streams
 * 
 * This script tests the NATS streams by publishing test data to each stream
 * and verifying that the data is received.
 * 
 * Usage:
 *   node test_nats_streams.js [--nats-url=<url>]
 */

const { connect, StringCodec } = require('nats');

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

// String codec for encoding/decoding NATS messages
const sc = StringCodec();

// List of streams to test
const streamsToTest = [
  { name: 'METRICS', subject: 'metrics.test' },
  { name: 'LOGS', subject: 'logs.test' },
  { name: 'ALERTS', subject: 'alerts.test' },
  { name: 'DEPLOYMENTS', subject: 'deployments.test' },
  { name: 'TRACES', subject: 'traces.test' },
  { name: 'ROOTCAUSES', subject: 'rootcause.test' },
  { name: 'POSTMORTEMS', subject: 'postmortems.test' },
  { name: 'RUNBOOKS', subject: 'runbooks.test' }
];

/**
 * Main function
 */
async function main() {
  console.log(`NATS Stream Test`);
  console.log(`----------------------------------------------`);
  console.log(`NATS URL: ${config.natsUrl}`);
  console.log(`----------------------------------------------`);
  
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
    
    // List all streams
    console.log('Listing all streams:');
    try {
      const streams = await js.streams.list().next();
      for (const stream of streams.streams) {
        console.log(`- ${stream.config.name}`);
      }
    } catch (error) {
      console.error(`Error listing streams: ${error.message}`);
    }
    
    // Test each stream
    console.log('\nTesting streams:');
    for (const stream of streamsToTest) {
      console.log(`\nTesting stream: ${stream.name}`);
      
      // Check if stream exists
      try {
        const streamInfo = await js.streams.info(stream.name);
        console.log(`Stream ${stream.name} exists with subjects: ${streamInfo.config.subjects.join(', ')}`);
        
        // Publish a test message
        const testData = {
          id: Math.random().toString(36).substring(2, 15),
          timestamp: new Date().toISOString(),
          message: `Test message for ${stream.name}`,
          test: true
        };
        
        await nc.publish(stream.subject, sc.encode(JSON.stringify(testData)));
        console.log(`Published test message to ${stream.subject}`);
        
        // Wait a bit for the message to be processed
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Get stream info again to see if message count increased
        const updatedStreamInfo = await js.streams.info(stream.name);
        console.log(`Stream ${stream.name} now has ${updatedStreamInfo.state.messages} messages`);
        
      } catch (error) {
        console.error(`Error testing stream ${stream.name}: ${error.message}`);
      }
    }
    
    // Disconnect from NATS
    await nc.drain();
    console.log('\nDisconnected from NATS server');
    
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
