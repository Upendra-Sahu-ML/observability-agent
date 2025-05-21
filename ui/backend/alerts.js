/**
 * Functions for handling alerts in the UI backend
 */

/**
 * Get historical alerts
 * @param {object} js - JetStream instance
 * @returns {Promise<Array>} - Historical alerts
 */
async function getHistoricalAlerts(js) {
  try {
    // Default historical alerts data as fallback
    const defaultAlerts = [
      {
        id: 'alert-default-1',
        labels: {
          alertname: 'NoAlertsAvailable',
          service: 'unknown-service',
          severity: 'unknown',
          instance: 'unknown',
          namespace: 'unknown'
        },
        annotations: {
          summary: 'No historical alerts available',
          description: 'No historical alert data is available at this time.'
        },
        startsAt: new Date().toISOString(),
        endsAt: new Date().toISOString(),
        status: 'unknown'
      }
    ];

    // If no JetStream, return default alerts
    if (!js) {
      console.warn('JetStream not available, returning default historical alerts');
      return defaultAlerts;
    }

    try {
      // Check if ALERTS stream exists
      let streamExists = false;
      try {
        // Handle different JetStream API versions
        if (typeof js.streams === 'object' && typeof js.streams.info === 'function') {
          await js.streams.info('ALERTS');
          streamExists = true;
        } else if (typeof js.streamInfo === 'function') {
          await js.streamInfo('ALERTS');
          streamExists = true;
        } else {
          throw new Error('Unknown JetStream API version');
        }
      } catch (streamErr) {
        console.warn(`ALERTS stream not found: ${streamErr.message}`);

        // Try to create the stream
        try {
          if (typeof js.streams === 'object' && typeof js.streams.add === 'function') {
            await js.streams.add({
              name: 'ALERTS',
              subjects: ['alerts.*']
            });
          } else if (typeof js.addStream === 'function') {
            await js.addStream({
              name: 'ALERTS',
              subjects: ['alerts.*']
            });
          } else {
            throw new Error('Unknown JetStream API version');
          }
          streamExists = true;
          console.log('Created ALERTS stream');
        } catch (createErr) {
          console.error(`Error creating ALERTS stream: ${createErr.message}`);
          return defaultAlerts;
        }
      }

      if (!streamExists) {
        return defaultAlerts;
      }

      // Create a consumer for the ALERTS stream
      let consumer;
      try {
        // Handle different JetStream API versions
        if (typeof js.consumers === 'object') {
          consumer = await js.consumers.get('ALERTS', 'alert-history-viewer').catch(async () => {
            // Create consumer if it doesn't exist
            return await js.consumers.add('ALERTS', {
              durable_name: 'alert-history-viewer',
              ack_policy: 'explicit',
              deliver_policy: 'all'
            });
          });
        } else {
          consumer = await js.getConsumer('ALERTS', 'alert-history-viewer').catch(async () => {
            // Create consumer if it doesn't exist
            return await js.addConsumer('ALERTS', {
              durable_name: 'alert-history-viewer',
              ack_policy: 'explicit',
              deliver_policy: 'all'
            });
          });
        }
      } catch (err) {
        console.error(`Error creating consumer: ${err.message}`);
        return defaultAlerts;
      }

      // Fetch alert messages
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
        console.error(`Error fetching alerts: ${err.message}`);
        return defaultAlerts;
      }

      // Process messages and collect alerts
      const alerts = [];

      for (const msg of messages) {
        try {
          // Use toString() to decode the message data
          const data = JSON.parse(msg.data.toString());

          alerts.push({
            ...data,
            id: data.id || `alert-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
            status: data.endsAt ? 'resolved' : (data.status || 'open')
          });

          // Acknowledge the message
          if (typeof msg.ack === 'function') {
            await msg.ack();
          }
        } catch (err) {
          console.error(`Error processing alert message: ${err.message}`);
          // Try to acknowledge the message even if processing failed
          if (typeof msg.ack === 'function') {
            await msg.ack();
          }
        }
      }

      // If no alerts were found, use default alerts
      if (alerts.length === 0) {
        console.warn('No historical alerts found in NATS, using default alerts');
        return defaultAlerts;
      }

      // Sort by start time, most recent first
      alerts.sort((a, b) => new Date(b.startsAt) - new Date(a.startsAt));

      return alerts;
    } catch (err) {
      console.warn(`Error fetching historical alerts: ${err.message}`);
      console.error('Error details:', err);
      return defaultAlerts;
    }
  } catch (error) {
    console.error('Error getting historical alerts:', error);
    return [];
  }
}

/**
 * Get active alerts
 * @param {object} js - JetStream instance
 * @returns {Promise<Array>} - Active alerts
 */
async function getActiveAlerts(js) {
  try {
    // Default active alerts data as fallback
    const defaultAlerts = [
      {
        id: 'alert-default-active-1',
        labels: {
          alertname: 'NoActiveAlerts',
          service: 'unknown-service',
          severity: 'unknown',
          instance: 'unknown',
          namespace: 'unknown'
        },
        annotations: {
          summary: 'No active alerts available',
          description: 'No active alert data is available at this time.'
        },
        startsAt: new Date().toISOString(),
        status: 'unknown'
      }
    ];

    // If no JetStream, return default alerts
    if (!js) {
      console.warn('JetStream not available, returning default active alerts');
      return defaultAlerts;
    }

    try {
      // Check if ALERTS stream exists - reuse the same stream as historical alerts
      let streamExists = false;
      try {
        // Handle different JetStream API versions
        if (typeof js.streams === 'object' && typeof js.streams.info === 'function') {
          await js.streams.info('ALERTS');
          streamExists = true;
        } else if (typeof js.streamInfo === 'function') {
          await js.streamInfo('ALERTS');
          streamExists = true;
        } else {
          throw new Error('Unknown JetStream API version');
        }
      } catch (streamErr) {
        console.warn(`ALERTS stream not found: ${streamErr.message}`);

        // Try to create the stream
        try {
          if (typeof js.streams === 'object' && typeof js.streams.add === 'function') {
            await js.streams.add({
              name: 'ALERTS',
              subjects: ['alerts.*']
            });
          } else if (typeof js.addStream === 'function') {
            await js.addStream({
              name: 'ALERTS',
              subjects: ['alerts.*']
            });
          } else {
            throw new Error('Unknown JetStream API version');
          }
          streamExists = true;
          console.log('Created ALERTS stream');
        } catch (createErr) {
          console.error(`Error creating ALERTS stream: ${createErr.message}`);
          return defaultAlerts;
        }
      }

      if (!streamExists) {
        return defaultAlerts;
      }

      // Create a consumer for the ALERTS stream
      let consumer;
      try {
        // Handle different JetStream API versions
        if (typeof js.consumers === 'object') {
          consumer = await js.consumers.get('ALERTS', 'alert-active-viewer').catch(async () => {
            // Create consumer if it doesn't exist
            return await js.consumers.add('ALERTS', {
              durable_name: 'alert-active-viewer',
              ack_policy: 'explicit',
              deliver_policy: 'all'
            });
          });
        } else {
          consumer = await js.getConsumer('ALERTS', 'alert-active-viewer').catch(async () => {
            // Create consumer if it doesn't exist
            return await js.addConsumer('ALERTS', {
              durable_name: 'alert-active-viewer',
              ack_policy: 'explicit',
              deliver_policy: 'all'
            });
          });
        }
      } catch (err) {
        console.error(`Error creating consumer: ${err.message}`);
        return defaultAlerts;
      }

      // Fetch alert messages
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
        console.error(`Error fetching alerts: ${err.message}`);
        return defaultAlerts;
      }

      // Process messages and collect alerts
      const allAlerts = [];

      for (const msg of messages) {
        try {
          // Use toString() to decode the message data
          const data = JSON.parse(msg.data.toString());

          allAlerts.push({
            ...data,
            id: data.id || `alert-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
            status: data.status || 'open'
          });

          // Acknowledge the message
          if (typeof msg.ack === 'function') {
            await msg.ack();
          }
        } catch (err) {
          console.error(`Error processing alert message: ${err.message}`);
          // Try to acknowledge the message even if processing failed
          if (typeof msg.ack === 'function') {
            await msg.ack();
          }
        }
      }

      // Filter for active alerts (no endsAt or endsAt in the future)
      const now = new Date();
      const activeAlerts = allAlerts.filter(alert =>
        !alert.endsAt || new Date(alert.endsAt) > now
      );

      // If no active alerts were found, use default alerts
      if (activeAlerts.length === 0) {
        console.warn('No active alerts found in NATS, using default alerts');
        return defaultAlerts;
      }

      // Sort by start time, most recent first
      activeAlerts.sort((a, b) => new Date(b.startsAt) - new Date(a.startsAt));

      return activeAlerts;
    } catch (err) {
      console.warn(`Error fetching active alerts: ${err.message}`);
      console.error('Error details:', err);
      return defaultAlerts;
    }
  } catch (error) {
    console.error('Error getting active alerts:', error);
    return [];
  }
}

module.exports = {
  getHistoricalAlerts,
  getActiveAlerts
};
