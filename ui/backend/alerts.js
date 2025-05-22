/**
 * Functions for handling alert data in the UI backend
 */

// Import the stream and consumer name constants and createConsumer function
const { STREAM_NAMES, CONSUMER_NAMES, createConsumer } = require('./constants');

/**
 * Get historical alerts from JetStream
 * @param {object} js - JetStream instance
 * @returns {Promise<Array>} - Array of historical alerts
 */
async function getHistoricalAlerts(js) {
  try {
    // Default alerts as fallback
    const defaultAlerts = [
      {
        id: 'alert-default-1',
        title: 'No historical alerts available',
        message: 'No historical alerts data is available at this time.',
        service: 'unknown-service',
        severity: 'unknown',
        status: 'resolved',
        timestamp: new Date().toISOString(),
        resolvedAt: new Date().toISOString(),
        rootCause: null
      }
    ];

    // If no JetStream, return default alerts
    if (!js) {
      console.warn('NATS JetStream not available, returning default historical alerts');
      return defaultAlerts;
    }

    // Get JetStreamManager from the wrapper if available
    const jsm = js._jsm || null;
    
    if (!jsm) {
      console.warn('JetStreamManager not available, returning default historical alerts');
      return defaultAlerts;
    }

    // Check if ALERTS stream exists
    let streamExists = false;
    try {
      await jsm.streams.info(STREAM_NAMES.ALERTS);
      streamExists = true;
    } catch (err) {
      streamExists = false;
    }

    if (!streamExists) {
      console.log(`${STREAM_NAMES.ALERTS} stream not found, returning default historical alerts`);
      return defaultAlerts;
    }

    // Create a consumer for the ALERTS stream using the utility function
    let consumer;
    try {
      consumer = await createConsumer(jsm, js, STREAM_NAMES.ALERTS, CONSUMER_NAMES.ALERTS_HISTORY);
    } catch (err) {
      console.error(`Error creating consumer for ${STREAM_NAMES.ALERTS}: ${err.message}`);
      return defaultAlerts;
    }

    // Fetch historical alert messages using the consumer
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
      console.error(`Error fetching historical alerts: ${err.message}`);
      return defaultAlerts;
    }

    // Process messages and collect historical alerts
    const StringCodec = require('nats').StringCodec;
    const sc = StringCodec();
    const alerts = [];

    for (const msg of messages) {
      try {
        // Handle both the old format and our new format with _parsedData property
        let data;
        if (msg._parsedData) {
          // Use pre-parsed data from our enhanced consumer
          data = msg._parsedData;
        } else if (msg.data) {
          // Try to decode and parse the data (old approach)
          try {
            if (Buffer.isBuffer(msg.data) || msg.data instanceof Uint8Array) {
              data = JSON.parse(sc.decode(msg.data));
            } else if (typeof msg.data === 'string') {
              data = JSON.parse(msg.data);
            } else {
              // If msg.data is already an object, use it directly
              data = msg.data;
            }
          } catch (parseErr) {
            console.warn(`Alert data parsing error: ${parseErr.message}. Using default alert.`);
            data = {
              id: `alert-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
              title: 'Alert with parsing error',
              message: 'Alert data could not be parsed properly.',
              service: 'unknown-service',
              severity: 'unknown',
              status: 'resolved',
              timestamp: new Date().toISOString(),
              resolvedAt: new Date().toISOString()
            };
          }
        } else {
          console.warn('Message has no data property, skipping');
          // Acknowledge and continue
          if (typeof msg.ack === 'function') {
            await msg.ack();
          }
          continue;
        }

        // Only include resolved alerts
        if (data.status === 'resolved') {
          alerts.push({
            id: data.id || `alert-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
            title: data.title || 'Unknown Alert',
            message: data.message || 'No additional information available',
            service: data.service || 'unknown-service',
            severity: data.severity || 'unknown',
            status: 'resolved',
            timestamp: data.timestamp || new Date().toISOString(),
            resolvedAt: data.resolvedAt || new Date().toISOString(),
            rootCause: data.rootCause || null
          });
        }

        // Acknowledge the message
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      } catch (err) {
        console.error(`Error processing historical alert message: ${err.message}`);
        // Try to acknowledge the message even if processing failed
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      }
    }

    // If no historical alerts were found, use default alerts
    if (alerts.length === 0) {
      console.warn('No historical alerts found in NATS, using default historical alerts');
      return defaultAlerts;
    }

    // Sort historical alerts by timestamp, most recent first
    alerts.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    return alerts;
  } catch (error) {
    console.error('Error getting historical alerts:', error);
    return [];
  }
}

/**
 * Get active alerts from JetStream
 * @param {object} js - JetStream instance
 * @returns {Promise<Array>} - Array of active alerts
 */
async function getActiveAlerts(js) {
  try {
    // Default alerts as fallback
    const defaultAlerts = [
      {
        id: 'alert-default-active-1',
        title: 'No active alerts available',
        message: 'No active alerts data is available at this time.',
        service: 'unknown-service',
        severity: 'unknown',
        status: 'active',
        timestamp: new Date().toISOString()
      }
    ];

    // If no JetStream, return default alerts
    if (!js) {
      console.warn('NATS JetStream not available, returning default active alerts');
      return defaultAlerts;
    }

    // Get JetStreamManager from the wrapper if available
    const jsm = js._jsm || null;
    
    if (!jsm) {
      console.warn('JetStreamManager not available, returning default active alerts');
      return defaultAlerts;
    }

    // Check if ALERTS stream exists
    let streamExists = false;
    try {
      await jsm.streams.info(STREAM_NAMES.ALERTS);
      streamExists = true;
    } catch (err) {
      streamExists = false;
    }

    if (!streamExists) {
      console.log(`${STREAM_NAMES.ALERTS} stream not found, returning default active alerts`);
      return defaultAlerts;
    }

    // Create a consumer for the ALERTS stream using the utility function
    let consumer;
    try {
      consumer = await createConsumer(jsm, js, STREAM_NAMES.ALERTS, CONSUMER_NAMES.ALERTS_ACTIVE);
    } catch (err) {
      console.error(`Error creating consumer for ${STREAM_NAMES.ALERTS}: ${err.message}`);
      return defaultAlerts;
    }

    // Fetch active alert messages
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
      console.error(`Error fetching active alerts: ${err.message}`);
      return defaultAlerts;
    }

    // Process messages and collect active alerts
    const StringCodec = require('nats').StringCodec;
    const sc = StringCodec();
    const alerts = [];

    for (const msg of messages) {
      try {
        // Handle both the old format and our new format with _parsedData property
        let data;
        if (msg._parsedData) {
          // Use pre-parsed data from our enhanced consumer
          data = msg._parsedData;
        } else if (msg.data) {
          // Try to decode and parse the data (old approach)
          try {
            if (Buffer.isBuffer(msg.data) || msg.data instanceof Uint8Array) {
              data = JSON.parse(sc.decode(msg.data));
            } else if (typeof msg.data === 'string') {
              data = JSON.parse(msg.data);
            } else {
              // If msg.data is already an object, use it directly
              data = msg.data;
            }
          } catch (parseErr) {
            console.warn(`Alert data parsing error: ${parseErr.message}. Using default alert.`);
            data = {
              id: `alert-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
              title: 'Alert with parsing error',
              message: 'Alert data could not be parsed properly.',
              service: 'unknown-service',
              severity: 'unknown',
              status: 'active',
              timestamp: new Date().toISOString()
            };
          }
        } else {
          console.warn('Message has no data property, skipping');
          // Acknowledge and continue
          if (typeof msg.ack === 'function') {
            await msg.ack();
          }
          continue;
        }

        // Only include active alerts
        if (data.status === 'active' || data.status === 'firing' || !data.resolvedAt) {
          alerts.push({
            id: data.id || `alert-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
            title: data.title || 'Unknown Alert',
            message: data.message || 'No additional information available',
            service: data.service || 'unknown-service',
            severity: data.severity || 'unknown',
            status: 'active',
            timestamp: data.timestamp || new Date().toISOString()
          });
        }

        // Acknowledge the message
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      } catch (err) {
        console.error(`Error processing active alert message: ${err.message}`);
        // Try to acknowledge the message even if processing failed
        if (typeof msg.ack === 'function') {
          await msg.ack();
        }
      }
    }

    // If no active alerts were found, use default active alerts
    if (alerts.length === 0) {
      console.warn('No active alerts found in NATS, using default active alerts');
      return defaultAlerts;
    }

    // Sort active alerts by timestamp, most recent first
    alerts.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    return alerts;
  } catch (error) {
    console.error('Error getting active alerts:', error);
    return [];
  }
}

module.exports = {
  getHistoricalAlerts,
  getActiveAlerts
};
