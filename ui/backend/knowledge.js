/**
 * Functions for handling knowledge base data in the UI backend
 */

/**
 * Get incidents from the knowledge base
 * @param {object} js - JetStream instance
 * @returns {Promise<Array>} - Incidents
 */
async function getIncidents(js) {
  try {
    if (js) {
      try {
        // Check if INCIDENTS collection exists in Qdrant
        // In a real implementation, we would query Qdrant directly
        // For now, we'll return mock data

        // This would be the real implementation:
        // const incidents = await qdrantClient.search({
        //   collection_name: "incidents",
        //   limit: 100
        // });
        // return incidents.map(hit => hit.payload);
      } catch (err) {
        console.warn(`Error fetching incidents from Qdrant: ${err.message}`);
        // Fall back to mock data
      }
    }

    // Mock incidents data
    return [
      {
        alert_id: 'alert-123',
        title: 'High CPU Usage in Payment Service',
        description: 'The payment service experienced high CPU usage, causing increased latency and timeouts.',
        root_cause: 'A memory leak in the payment processing component caused excessive CPU usage during transaction processing.',
        resolution: 'Fixed memory leak in the payment processing component and deployed a hotfix.',
        service: 'payment-service',
        timestamp: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days ago
        metadata: {
          severity: 'critical',
          duration: '45 minutes',
          affected_users: '~500',
          impact: 'Payment processing delayed'
        }
      },
      {
        alert_id: 'alert-456',
        title: 'Database Connection Pool Exhaustion',
        description: 'The order service was unable to process new orders due to database connection pool exhaustion.',
        root_cause: 'Connection leaks in the order processing workflow were not properly closing database connections.',
        resolution: 'Implemented connection handling improvements and increased the connection pool size.',
        service: 'order-service',
        timestamp: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(), // 14 days ago
        metadata: {
          severity: 'critical',
          duration: '30 minutes',
          affected_users: '~300',
          impact: 'Order processing halted'
        }
      },
      {
        alert_id: 'alert-789',
        title: 'API Gateway High Latency',
        description: 'The API gateway experienced high latency, affecting all downstream services.',
        root_cause: 'Increased traffic combined with inefficient routing logic caused bottlenecks in the API gateway.',
        resolution: 'Optimized routing logic and scaled up the API gateway instances.',
        service: 'api-gateway',
        timestamp: new Date(Date.now() - 21 * 24 * 60 * 60 * 1000).toISOString(), // 21 days ago
        metadata: {
          severity: 'warning',
          duration: '60 minutes',
          affected_users: '~1000',
          impact: 'Increased response times'
        }
      }
    ];
  } catch (error) {
    console.error('Error getting incidents:', error);
    return [];
  }
}

/**
 * Get postmortems from the knowledge base
 * @param {object} js - JetStream instance
 * @returns {Promise<Array>} - Postmortems
 */
async function getPostmortems(js) {
  try {
    if (js) {
      try {
        // Check if POSTMORTEMS stream exists
        const streamInfo = await js.stream_info('POSTMORTEMS').catch(() => null);

        if (streamInfo) {
          // Get postmortems from JetStream
          const consumer = await js.consumer('POSTMORTEMS', 'postmortem-viewer').catch(async () => {
            // Create consumer if it doesn't exist
            return await js.add_consumer('POSTMORTEMS', {
              durable_name: 'postmortem-viewer',
              ack_policy: 'explicit',
              deliver_policy: 'all'
            });
          });

          const messages = await consumer.fetch({ max_messages: 100 });

          const postmortems = messages.map(msg => {
            // Use toString() to decode the message data
            const data = JSON.parse(msg.data.toString());
            msg.ack();
            return data;
          });

          return postmortems;
        }
      } catch (err) {
        console.warn(`Error fetching postmortems from JetStream: ${err.message}`);
        // Fall back to mock data
      }
    }

    // Mock postmortems data
    return [
      {
        id: 'pm-123',
        alert_id: 'alert-123',
        title: 'Payment Service Outage - CPU Usage',
        summary: 'The payment service experienced high CPU usage, causing increased latency and timeouts.',
        status: 'completed',
        service: 'payment-service',
        createdAt: new Date(Date.now() - 6 * 24 * 60 * 60 * 1000).toISOString(), // 6 days ago
        content: `# Payment Service Outage Postmortem

## Incident Summary
- **Date**: ${new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toLocaleDateString()}
- **Duration**: 45 minutes
- **Impact**: Payment processing delayed for approximately 500 users

## Root Cause
A memory leak in the payment processing component caused excessive CPU usage during transaction processing.

## Timeline
- **10:15 AM**: Alert triggered for high CPU usage in payment service
- **10:20 AM**: On-call engineer acknowledged the alert
- **10:25 AM**: Identified high memory usage in payment processing component
- **10:40 AM**: Deployed hotfix to address memory leak
- **11:00 AM**: Service returned to normal operation

## Resolution
Fixed memory leak in the payment processing component and deployed a hotfix.

## Action Items
1. Implement better memory usage monitoring
2. Add automated tests to catch memory leaks
3. Review error handling in payment processing workflow
4. Update runbook with memory leak detection steps`
      },
      {
        id: 'pm-456',
        alert_id: 'alert-456',
        title: 'Order Service Outage - Database Connections',
        summary: 'The order service was unable to process new orders due to database connection pool exhaustion.',
        status: 'completed',
        service: 'order-service',
        createdAt: new Date(Date.now() - 13 * 24 * 60 * 60 * 1000).toISOString(), // 13 days ago
        content: `# Order Service Outage Postmortem

## Incident Summary
- **Date**: ${new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toLocaleDateString()}
- **Duration**: 30 minutes
- **Impact**: Order processing halted for approximately 300 users

## Root Cause
Connection leaks in the order processing workflow were not properly closing database connections.

## Timeline
- **2:30 PM**: Alert triggered for database connection pool exhaustion
- **2:35 PM**: On-call engineer acknowledged the alert
- **2:40 PM**: Identified connection leaks in order processing workflow
- **2:50 PM**: Implemented connection handling improvements
- **3:00 PM**: Service returned to normal operation

## Resolution
Implemented connection handling improvements and increased the connection pool size.

## Action Items
1. Implement connection pool monitoring
2. Add automated tests for connection handling
3. Review all database access code for proper connection management
4. Update runbook with connection pool troubleshooting steps`
      }
    ];
  } catch (error) {
    console.error('Error getting postmortems:', error);
    return [];
  }
}

module.exports = {
  getIncidents,
  getPostmortems
};
