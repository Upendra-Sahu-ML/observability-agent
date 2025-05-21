/**
 * Functions for handling knowledge base data in the UI backend
 */
const axios = require('axios');

// Get Qdrant URL from environment variable or use default
// Add fallback URLs in case the primary URL is not accessible
const QDRANT_URL = process.env.QDRANT_URL || 'http://qdrant:6333';
const QDRANT_FALLBACK_URLS = [
  'http://localhost:6333',
  'http://qdrant.observability:6333',
  'http://qdrant-service:6333'
];

/**
 * Get incidents from the knowledge base
 * @param {object} js - JetStream instance
 * @returns {Promise<Array>} - Incidents
 */
async function getIncidents(js) {
  try {
    // Default incidents data as fallback
    const defaultIncidents = [
      {
        alert_id: 'alert-default-1',
        title: 'No incidents available',
        description: 'No incident data is available at this time.',
        root_cause: 'Unknown',
        resolution: 'Unknown',
        service: 'unknown-service',
        timestamp: new Date().toISOString(),
        metadata: {
          severity: 'unknown',
          duration: 'unknown',
          affected_users: 'unknown',
          impact: 'unknown'
        }
      }
    ];

    // Try to fetch incidents from Qdrant
    try {
      console.log(`Attempting to connect to Qdrant at ${QDRANT_URL}`);

      // Try the primary URL first, then fallback URLs if needed
      let collectionsResponse;
      let currentUrl = QDRANT_URL;
      let connected = false;

      try {
        // Try the primary URL
        collectionsResponse = await axios.get(`${currentUrl}/collections`);
        connected = true;
      } catch (primaryErr) {
        console.warn(`Failed to connect to primary Qdrant URL ${currentUrl}: ${primaryErr.message}`);

        // Try fallback URLs
        for (const fallbackUrl of QDRANT_FALLBACK_URLS) {
          try {
            console.log(`Trying fallback Qdrant URL: ${fallbackUrl}`);
            collectionsResponse = await axios.get(`${fallbackUrl}/collections`);
            currentUrl = fallbackUrl;
            connected = true;
            console.log(`Successfully connected to Qdrant at ${currentUrl}`);
            break;
          } catch (fallbackErr) {
            console.warn(`Failed to connect to fallback Qdrant URL ${fallbackUrl}: ${fallbackErr.message}`);
          }
        }
      }

      // If we couldn't connect to any Qdrant instance, return default incidents
      if (!connected || !collectionsResponse) {
        console.warn('Could not connect to any Qdrant instance');
        return defaultIncidents;
      }

      const collections = collectionsResponse.data.result || [];

      const incidentsCollectionExists = collections.some(collection =>
        collection.name === 'incidents'
      );

      if (!incidentsCollectionExists) {
        console.warn('INCIDENTS collection does not exist in Qdrant');
        return defaultIncidents;
      }

      // Search for incidents in Qdrant
      const searchResponse = await axios.post(`${currentUrl}/collections/incidents/points/search`, {
        vector: null,  // Perform a match-all query
        limit: 100,
        with_payload: true
      });

      const incidents = searchResponse.data.result || [];

      if (incidents.length === 0) {
        console.warn('No incidents found in Qdrant');
        return defaultIncidents;
      }

      // Map Qdrant results to incident objects
      const mappedIncidents = incidents.map(hit => hit.payload);

      // Sort incidents by timestamp, most recent first
      mappedIncidents.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

      return mappedIncidents;
    } catch (err) {
      console.warn(`Error fetching incidents from Qdrant: ${err.message}`);
      console.error('Qdrant error details:', err);

      // If we have JetStream, try to get incidents from there as fallback
      if (js) {
        try {
          // Check if INCIDENTS stream exists
          const streamExists = await js.streamInfo('INCIDENTS').catch(() => false);

          if (streamExists) {
            // Create a consumer for the INCIDENTS stream
            const consumer = await js.getConsumer('INCIDENTS', 'incident-viewer').catch(async () => {
              // Create consumer if it doesn't exist
              return await js.addConsumer('INCIDENTS', {
                durable_name: 'incident-viewer',
                ack_policy: 'explicit',
                deliver_policy: 'all'
              });
            });

            // Fetch incident messages
            const fetchOptions = { max_messages: 100 };
            const messages = await consumer.fetch(fetchOptions);

            // Process messages and collect incidents
            const incidents = [];

            for (const msg of messages) {
              try {
                const data = JSON.parse(msg.data.toString());
                incidents.push(data);

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

            if (incidents.length > 0) {
              // Sort incidents by timestamp, most recent first
              incidents.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
              return incidents;
            }
          }
        } catch (jsErr) {
          console.warn(`Error fetching incidents from JetStream: ${jsErr.message}`);
        }
      }

      // Fall back to default incidents
      return defaultIncidents;
    }
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
    // Default postmortems data as fallback
    const defaultPostmortems = [
      {
        id: 'pm-default-1',
        alert_id: 'alert-unknown',
        title: 'No postmortems available',
        summary: 'No postmortem data is available at this time.',
        status: 'unknown',
        service: 'unknown-service',
        createdAt: new Date().toISOString(),
        content: '# No postmortem content available'
      }
    ];

    // If no JetStream, return default postmortems
    if (!js) {
      console.warn('JetStream not available, returning default postmortem data');
      return defaultPostmortems;
    }

    // Try to fetch postmortems from JetStream
    try {
      // Check if POSTMORTEMS stream exists
      const streamExists = await js.streamInfo('POSTMORTEMS').catch(() => false);

      if (!streamExists) {
        console.warn('POSTMORTEMS stream does not exist');

        // Try to create the stream
        try {
          await js.addStream({
            name: 'POSTMORTEMS',
            subjects: ['postmortems.*']
          });
          console.log('Created POSTMORTEMS stream');
        } catch (createErr) {
          console.error(`Error creating POSTMORTEMS stream: ${createErr.message}`);
          return defaultPostmortems;
        }
      }

      // Create a consumer for the POSTMORTEMS stream
      let consumer;
      try {
        consumer = await js.getConsumer('POSTMORTEMS', 'postmortem-viewer').catch(async () => {
          // Create consumer if it doesn't exist
          return await js.addConsumer('POSTMORTEMS', {
            durable_name: 'postmortem-viewer',
            ack_policy: 'explicit',
            deliver_policy: 'all'
          });
        });
      } catch (err) {
        console.error(`Error creating consumer: ${err.message}`);
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
      const postmortems = [];

      for (const msg of messages) {
        try {
          const data = JSON.parse(msg.data.toString());

          // Ensure the postmortem has the required fields
          if (data.title) {
            postmortems.push({
              id: data.id || `pm-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
              alert_id: data.alert_id || data.alertId || 'unknown',
              title: data.title,
              summary: data.summary || 'No summary available',
              status: data.status || 'unknown',
              service: data.service || 'unknown-service',
              createdAt: data.createdAt || data.timestamp || new Date().toISOString(),
              content: data.content || '# No content available'
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

      // If no postmortems were found, try to fetch from Qdrant
      if (postmortems.length === 0) {
        console.warn('No postmortems found in JetStream, trying Qdrant');

        try {
          console.log(`Attempting to connect to Qdrant at ${QDRANT_URL}`);

          // Try the primary URL first, then fallback URLs if needed
          let collectionsResponse;
          let currentUrl = QDRANT_URL;
          let connected = false;

          try {
            // Try the primary URL
            collectionsResponse = await axios.get(`${currentUrl}/collections`);
            connected = true;
          } catch (primaryErr) {
            console.warn(`Failed to connect to primary Qdrant URL ${currentUrl}: ${primaryErr.message}`);

            // Try fallback URLs
            for (const fallbackUrl of QDRANT_FALLBACK_URLS) {
              try {
                console.log(`Trying fallback Qdrant URL: ${fallbackUrl}`);
                collectionsResponse = await axios.get(`${fallbackUrl}/collections`);
                currentUrl = fallbackUrl;
                connected = true;
                console.log(`Successfully connected to Qdrant at ${currentUrl}`);
                break;
              } catch (fallbackErr) {
                console.warn(`Failed to connect to fallback Qdrant URL ${fallbackUrl}: ${fallbackErr.message}`);
              }
            }
          }

          // If we couldn't connect to any Qdrant instance, return default postmortems
          if (!connected || !collectionsResponse) {
            console.warn('Could not connect to any Qdrant instance');
            return defaultPostmortems;
          }

          const collections = collectionsResponse.data.result || [];

          const postmortemsCollectionExists = collections.some(collection =>
            collection.name === 'postmortems'
          );

          if (postmortemsCollectionExists) {
            // Search for postmortems in Qdrant
            const searchResponse = await axios.post(`${currentUrl}/collections/postmortems/points/search`, {
              vector: null,  // Perform a match-all query
              limit: 100,
              with_payload: true
            });

            const qdrantPostmortems = searchResponse.data.result || [];

            if (qdrantPostmortems.length > 0) {
              // Map Qdrant results to postmortem objects
              const mappedPostmortems = qdrantPostmortems.map(hit => hit.payload);

              // Sort postmortems by createdAt, most recent first
              mappedPostmortems.sort((a, b) => new Date(b.createdAt || b.timestamp) - new Date(a.createdAt || a.timestamp));

              return mappedPostmortems;
            }
          }
        } catch (qdrantErr) {
          console.warn(`Error fetching postmortems from Qdrant: ${qdrantErr.message}`);
        }

        // If still no postmortems, return default
        if (postmortems.length === 0) {
          return defaultPostmortems;
        }
      }

      // Sort postmortems by createdAt, most recent first
      postmortems.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

      return postmortems;
    } catch (err) {
      console.warn(`Error fetching postmortems: ${err.message}`);
      return defaultPostmortems;
    }
  } catch (error) {
    console.error('Error getting postmortems:', error);
    return [];
  }
}

module.exports = {
  getIncidents,
  getPostmortems
};
