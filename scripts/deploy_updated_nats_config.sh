#!/bin/bash
# Script to deploy the updated NATS configuration

set -e

echo "Deploying updated NATS configuration..."

# Update the UI backend code
echo "Updating UI backend code..."
node update_ui_backend_nats.js

# Update the test scripts
echo "Updating test scripts..."
node update_test_scripts.js

# Build and push the UI backend image
echo "Building and pushing UI backend image..."
cd ../ui/backend
docker build -t docker.io/upendrasahu/observability-agent-ui-backend:1.3.4 .
docker push docker.io/upendrasahu/observability-agent-ui-backend:1.3.4

# Update the Helm chart values to use the new image
cd ../../helm/observability-agent
echo "Updating Helm chart values..."
sed -i '' 's/tag: "1.3.3"/tag: "1.3.4"/' values.yaml

# Upgrade the Helm release
echo "Upgrading Helm release..."
helm upgrade observability-agent . -n observability

echo "Waiting for pods to restart..."
sleep 30

# Check the status of the pods
echo "Checking pod status..."
kubectl get pods -n observability

echo "Deployment complete!"
