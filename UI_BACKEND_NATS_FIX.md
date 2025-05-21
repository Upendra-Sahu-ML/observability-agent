# UI Backend and NATS Integration Fix

This document provides instructions on how to fix the integration between the UI backend and NATS JetStream.

## Problem

The UI backend is not properly configured to use the JetStream domain when connecting to NATS. This causes the following issues:

1. The UI backend is unable to access streams in the NATS server.
2. The UI backend falls back to using mock data instead of real-time data from NATS.
3. Error messages like "JetStream API does not support adding consumers, using fallback" and "Using mock consumer fetch" appear in the logs.

## Solution

The solution involves the following steps:

1. Update the UI backend code to properly handle the JetStream domain.
2. Create the required streams in NATS with the correct domain.
3. Publish test data to the streams to verify the integration.

## Changes Made

The following changes have been made to fix the issue:

1. **Updated UI Backend Code** (`ui/backend/server.js`):
   - Added JetStream domain support to the NATS connection
   - Fixed the JetStream API compatibility wrapper
   - Added proper error handling and fallback mechanisms

2. **Updated Dockerfile** (`ui/backend/Dockerfile`):
   - Added NATS_DOMAIN environment variable

3. **Scripts for Testing and Deployment**:
   - `scripts/create_ui_streams.js` - Script to create the required streams in NATS with the correct domain
   - `scripts/publish_test_data.js` - Script to publish test data to the streams
   - `scripts/test_nats_connection.js` - Script to test the NATS connection and list streams and consumers
   - `scripts/build_deploy_ui_backend.sh` - Script to build and deploy the updated UI backend

## Step-by-Step Instructions

### 1. Test the NATS Connection

First, let's test the connection to NATS and see what streams are available:

```bash
# Port forward to the NATS server
kubectl port-forward -n observability svc/observability-agent-nats 4222:4222

# In another terminal, run the test script
cd scripts
node test_nats_connection.js
```

### 2. Create the Required Streams

Create the required streams in NATS with the correct domain:

```bash
# Port forward to the NATS server (if not already done)
kubectl port-forward -n observability svc/observability-agent-nats 4222:4222

# In another terminal, run the create streams script
cd scripts
node create_ui_streams.js
```

### 3. Publish Test Data

Publish some test data to the streams to verify they are working:

```bash
# Port forward to the NATS server (if not already done)
kubectl port-forward -n observability svc/observability-agent-nats 4222:4222

# In another terminal, run the publish_with_domain.js script
cd scripts
node publish_with_domain.js --domain=observability-agent --count=20
```

For more detailed information about the available data publishing scripts, please refer to the [Data Publishing Guide](DATA_PUBLISHING_GUIDE.md).

### 4. Build and Deploy the Updated UI Backend

Build and deploy the updated UI backend:

```bash
# Set the registry and tag
export REGISTRY=docker.io/upendrasahu
export TAG=<NEW_TAG>

# Run the build and deploy script
cd scripts
./build_deploy_ui_backend.sh
```

### 5. Verify the Fix

After deploying the updated UI backend, verify that it's now receiving data from NATS:

```bash
# Check the logs of the UI backend
kubectl logs -n observability deployment/observability-agent-ui-backend
```

You should no longer see error messages like "JetStream API does not support adding consumers, using fallback" and "Using mock consumer fetch". Instead, you should see messages indicating that the UI backend is successfully connecting to NATS and receiving data.

## Key Changes Made

1. **Added JetStream Domain to Connection Options**: The UI backend now includes the JetStream domain in the NATS connection options.

   ```javascript
   nc = await connect({
     servers: NATS_URL,
     timeout: 5000,
     debug: process.env.DEBUG === 'true',
     jetstreamDomain: NATS_DOMAIN // Add JetStream domain to connection options
   });
   ```

2. **Added NATS_DOMAIN Environment Variable**: The UI backend now accepts a NATS_DOMAIN environment variable to specify the JetStream domain.

   ```javascript
   const NATS_DOMAIN = process.env.NATS_DOMAIN || 'observability-agent';
   ```

3. **Updated JetStream API Compatibility Wrapper**: The JetStream API compatibility wrapper now properly handles domain-specific API calls.

4. **Created Scripts for Stream Management**: Scripts have been created to manage streams and consumers in NATS with the correct domain.

## Troubleshooting

If you're still experiencing issues after applying the fix, try the following:

1. **Check NATS Connection**: Make sure the UI backend can connect to NATS by checking the logs.

2. **Verify Streams Exist**: Use the `test_nats_connection.js` script to verify that the required streams exist in NATS.

3. **Check Domain Configuration**: Make sure the NATS server is configured with the correct domain in the `nats.conf` file.

4. **Restart the UI Backend**: Try restarting the UI backend deployment to ensure it picks up the new configuration.

5. **Check for Errors**: Look for any error messages in the UI backend logs that might indicate what's going wrong.

## Conclusion

By following these steps, you should be able to fix the integration between the UI backend and NATS JetStream. The UI backend will now properly connect to NATS with the correct domain and receive real-time data instead of falling back to mock data.
