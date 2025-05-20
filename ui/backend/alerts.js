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
    if (js) {
      try {
        // Check if ALERTS stream exists
        const streamInfo = await js.streams.info('ALERTS').catch(() => null);

        if (streamInfo) {
          // Get alerts from JetStream
          const consumer = await js.consumers.get('ALERTS', 'alert-history-viewer').catch(async () => {
            // Create consumer if it doesn't exist
            return await js.consumers.add('ALERTS', {
              durable_name: 'alert-history-viewer',
              ack_policy: 'explicit',
              deliver_policy: 'all'
            });
          });

          const messages = await consumer.fetch({ max_messages: 100 });

          const alerts = messages.map(msg => {
            // Use the StringCodec from the NATS library to decode the message data
            const data = JSON.parse(msg.data.toString());
            msg.ack();
            return {
              ...data,
              status: data.endsAt ? 'resolved' : (data.status || 'open')
            };
          });

          // Sort by start time, most recent first
          return alerts.sort((a, b) => new Date(b.startsAt) - new Date(a.startsAt));
        }
      } catch (err) {
        console.warn(`Error fetching alerts from JetStream: ${err.message}`);
        // Fall back to mock data
      }
    }

    // Mock historical alerts data
    return [
      {
        id: 'alert-123',
        labels: {
          alertname: 'HighCpuUsage',
          service: 'payment-service',
          severity: 'critical',
          instance: 'instance-1',
          namespace: 'default'
        },
        annotations: {
          summary: 'High CPU usage detected',
          description: 'CPU usage above threshold for payment-service',
          value: '92%',
          threshold: '80%'
        },
        startsAt: '2023-08-15T10:30:00Z',
        endsAt: '2023-08-15T10:45:00Z',
        status: 'resolved'
      },
      {
        id: 'alert-456',
        labels: {
          alertname: 'HighMemoryUsage',
          service: 'order-service',
          severity: 'warning',
          instance: 'instance-2',
          namespace: 'default'
        },
        annotations: {
          summary: 'High memory usage detected',
          description: 'Memory usage above threshold for order-service',
          value: '87%',
          threshold: '85%'
        },
        startsAt: '2023-08-15T11:15:00Z',
        endsAt: '2023-08-15T11:30:00Z',
        status: 'resolved'
      },
      {
        id: 'alert-789',
        labels: {
          alertname: 'HighLatency',
          service: 'api-gateway',
          severity: 'warning',
          endpoint: '/api/v1/orders',
          namespace: 'default'
        },
        annotations: {
          summary: 'High latency detected',
          description: 'Request latency above threshold',
          value: '2.5s',
          threshold: '1s'
        },
        startsAt: '2023-08-15T12:00:00Z',
        endsAt: '2023-08-15T12:20:00Z',
        status: 'resolved'
      }
    ];
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
    if (js) {
      try {
        // Check if ALERTS stream exists
        const streamInfo = await js.streams.info('ALERTS').catch(() => null);

        if (streamInfo) {
          // Get alerts from JetStream
          const consumer = await js.consumers.get('ALERTS', 'alert-active-viewer').catch(async () => {
            // Create consumer if it doesn't exist
            return await js.consumers.add('ALERTS', {
              durable_name: 'alert-active-viewer',
              ack_policy: 'explicit',
              deliver_policy: 'all'
            });
          });

          const messages = await consumer.fetch({ max_messages: 100 });

          const allAlerts = messages.map(msg => {
            // Use the StringCodec from the NATS library to decode the message data
            const data = JSON.parse(msg.data.toString());
            msg.ack();
            return {
              ...data,
              status: data.status || 'open'
            };
          });

          // Filter for active alerts (no endsAt or endsAt in the future)
          const now = new Date();
          const activeAlerts = allAlerts.filter(alert =>
            !alert.endsAt || new Date(alert.endsAt) > now
          );

          // Sort by start time, most recent first
          return activeAlerts.sort((a, b) => new Date(b.startsAt) - new Date(a.startsAt));
        }
      } catch (err) {
        console.warn(`Error fetching active alerts from JetStream: ${err.message}`);
        // Fall back to mock data
      }
    }

    // Mock active alerts data
    return [
      {
        id: 'alert-101',
        labels: {
          alertname: 'HighErrorRate',
          service: 'payment-service',
          severity: 'critical',
          error_type: '5xx',
          namespace: 'default'
        },
        annotations: {
          summary: 'High error rate detected',
          description: 'Error rate above threshold for payment-service',
          value: '15.5%',
          threshold: '5%'
        },
        startsAt: new Date(Date.now() - 15 * 60 * 1000).toISOString(), // 15 minutes ago
        status: 'open'
      },
      {
        id: 'alert-102',
        labels: {
          alertname: 'DeploymentFailed',
          service: 'inventory-service',
          severity: 'critical',
          version: 'v1.5.0',
          namespace: 'default'
        },
        annotations: {
          summary: 'Deployment failed',
          description: 'Deployment of inventory-service v1.5.0 failed',
          status: 'failed'
        },
        startsAt: new Date(Date.now() - 30 * 60 * 1000).toISOString(), // 30 minutes ago
        status: 'acknowledged'
      },
      {
        id: 'alert-103',
        labels: {
          alertname: 'HighLatency',
          service: 'api-gateway',
          severity: 'warning',
          endpoint: '/api/v1/products',
          namespace: 'default'
        },
        annotations: {
          summary: 'High latency detected',
          description: 'Request latency above threshold',
          value: '1.8s',
          threshold: '1s'
        },
        startsAt: new Date(Date.now() - 10 * 60 * 1000).toISOString(), // 10 minutes ago
        status: 'in_progress'
      }
    ];
  } catch (error) {
    console.error('Error getting active alerts:', error);
    return [];
  }
}

module.exports = {
  getHistoricalAlerts,
  getActiveAlerts
};
