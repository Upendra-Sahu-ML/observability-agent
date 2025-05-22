/**
 * Functions for handling knowledge base data in the UI backend
 */

// Import the stream and consumer name constants and createConsumer function
const { STREAM_NAMES, CONSUMER_NAMES, createConsumer } = require('./constants');

/**
 * Get incident data from the knowledge base
 * @param {object} js - JetStream instance
 * @returns {Promise<Array>} - Array of incidents
 */
async function getIncidents(js) {
  try {
    // Default incidents as fallback
    const defaultIncidents = [
      {
        id: 'incident-default-1',
        title: 'No incidents available',
        service: 'unknown-service',
        status: 'closed',
        createdAt: new Date().toISOString(),
        closedAt: new Date().toISOString(),
        summary: 'No incident data is available at this time.',
        impact: 'Unknown',
        owner: 'Unknown'
      }
    ];

    // If no JetStream, return default incidents
    if (!js) {
      console.warn('NATS JetStream not available, returning default incidents');
      return defaultIncidents;
    }

    // Get JetStreamManager from the wrapper if available
    const jsm = js._jsm || null;
    
    if (!jsm) {
      console.warn('JetStreamManager not available, returning default incidents');
      return defaultIncidents;
    }

    // Check if NOTEBOOKS stream exists (used for incidents)
    let streamExists = false;
    try {
      await jsm.streams.info(STREAM_NAMES.NOTEBOOKS);
      streamExists = true;
    } catch (err) {
      streamExists = false;
    }

    if (!streamExists) {
      console.log(`${STREAM_NAMES.NOTEBOOKS} stream not found, returning default incidents`);
      return defaultIncidents;
    }

    // Create a consumer for the NOTEBOOKS stream using the utility function
    let consumer;
    try {
      consumer = await createConsumer(jsm, js, STREAM_NAMES.NOTEBOOKS, 'incidents-viewer');
    } catch (err) {
      console.error(`Error creating consumer for ${STREAM_NAMES.NOTEBOOKS}: ${err.message}`);
      return defaultIncidents;
    }

    // Fetch incident messages
    let messages = [];
    try {
      const fetchOptions = { max_messages: 100 };
      if (typeof consumer.fetch === 'function') {
        messages = await consumer.fetch(fetchOptions);
      } else if (typeof consumer.pull === 'function') {
        messages = await consumer.pull(fetchOptions.max_messages);
      } else {
        throw new Error('Consumer does not support fetch or pull');
      }
    } catch (err) {
      console.error(`Error fetching incidents: ${err.message}`);
      return defaultIncidents;
    }

    // Process messages and collect incidents
    const StringCodec = require('nats').StringCodec;
    const sc = StringCodec();
    const incidents = [];

    for (const msg of messages) {
      try {
        const data = JSON.parse(sc.decode(msg.data));

        // Only include notebook entries that are incidents
        if (data.type === 'incident') {
          incidents.push({
            id: data.id || `incident-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
            title: data.title || 'Unknown Incident',
            service: data.service || 'unknown-service',
            status: data.status || 'closed',
            createdAt: data.createdAt || data.timestamp || new Date().toISOString(),
            closedAt: data.closedAt || data.resolvedAt || new Date().toISOString(),
            summary: data.summary || 'No summary available',
            impact: data.impact || 'Unknown',
            owner: data.owner || 'Unknown'
          });
        }

        // Acknowledge the message
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      } catch (err) {
        console.error(`Error processing incident message: ${err.message}`);
        // Try to acknowledge the message even if processing failed
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      }
    }

    // If no incidents were found, use default incidents
    if (incidents.length === 0) {
      console.warn('No incidents found in NATS, using default incidents');
      return defaultIncidents;
    }

    // Sort incidents by createdAt, most recent first
    incidents.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

    return incidents;
  } catch (error) {
    console.error('Error getting incidents:', error);
    return [];
  }
}

/**
 * Get postmortem data from the knowledge base
 * @param {object} js - JetStream instance
 * @returns {Promise<Array>} - Array of postmortems
 */
async function getPostmortems(js) {
  try {
    // Default postmortems as fallback
    const defaultPostmortems = [
      {
        id: 'pm-kb-default-1',
        title: 'No postmortems available in knowledge base',
        status: 'completed',
        createdAt: new Date().toISOString(),
        summary: 'No postmortem data is available in the knowledge base at this time.',
        impact: 'Unknown',
        rootCause: 'Unknown',
        resolution: 'Unknown',
        actionItems: ['No action items available']
      }
    ];

    // If no JetStream, return default postmortems
    if (!js) {
      console.warn('NATS JetStream not available, returning default postmortems');
      return defaultPostmortems;
    }

    // Get JetStreamManager from the wrapper if available
    const jsm = js._jsm || null;
    
    if (!jsm) {
      console.warn('JetStreamManager not available, returning default postmortems');
      return defaultPostmortems;
    }

    // Check if NOTEBOOKS stream exists (used for postmortems)
    let streamExists = false;
    try {
      await jsm.streams.info(STREAM_NAMES.NOTEBOOKS);
      streamExists = true;
    } catch (err) {
      streamExists = false;
    }

    if (!streamExists) {
      console.log(`${STREAM_NAMES.NOTEBOOKS} stream not found, returning default postmortems`);
      return defaultPostmortems;
    }

    // Create a consumer for the NOTEBOOKS stream using the utility function
    let consumer;
    try {
      consumer = await createConsumer(jsm, js, STREAM_NAMES.NOTEBOOKS, 'postmortems-kb-viewer');
    } catch (err) {
      console.error(`Error creating consumer for ${STREAM_NAMES.NOTEBOOKS}: ${err.message}`);
      return defaultPostmortems;
    }

    // Fetch postmortem messages
    let messages = [];
    try {
      const fetchOptions = { max_messages: 100 };
      if (typeof consumer.fetch === 'function') {
        messages = await consumer.fetch(fetchOptions);
      } else if (typeof consumer.pull === 'function') {
        messages = await consumer.pull(fetchOptions.max_messages);
      } else {
        throw new Error('Consumer does not support fetch or pull');
      }
    } catch (err) {
      console.error(`Error fetching postmortems: ${err.message}`);
      return defaultPostmortems;
    }

    // Process messages and collect postmortems
    const StringCodec = require('nats').StringCodec;
    const sc = StringCodec();
    const postmortems = [];

    for (const msg of messages) {
      try {
        const data = JSON.parse(sc.decode(msg.data));

        // Only include notebook entries that are postmortems
        if (data.type === 'postmortem') {
          postmortems.push({
            id: data.id || `pm-kb-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
            title: data.title || 'Unknown Postmortem',
            status: data.status || 'completed',
            createdAt: data.createdAt || data.timestamp || new Date().toISOString(),
            summary: data.summary || 'No summary available',
            impact: data.impact || 'Unknown',
            rootCause: data.rootCause || 'Unknown',
            resolution: data.resolution || 'Unknown',
            actionItems: Array.isArray(data.actionItems) ? data.actionItems : ['No action items available']
          });
        }

        // Acknowledge the message
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      } catch (err) {
        console.error(`Error processing postmortem message: ${err.message}`);
        // Try to acknowledge the message even if processing failed
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      }
    }

    // If no postmortems were found, use default postmortems
    if (postmortems.length === 0) {
      console.warn('No postmortems found in NATS, using default postmortems');
      return defaultPostmortems;
    }

    // Sort postmortems by createdAt, most recent first
    postmortems.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

    return postmortems;
  } catch (error) {
    console.error('Error getting postmortems:', error);
    return [];
  }
}

module.exports = {
  getIncidents,
  getPostmortems
};
