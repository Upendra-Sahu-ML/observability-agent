#!/bin/bash
# Script to build and deploy the UI container with the fixed theme

# Set the namespace
NAMESPACE="observability"
REGISTRY="localhost:5000"
TAG="latest"

# Build the UI container
echo "Building the UI container..."
cd ../ui
docker build -t ${REGISTRY}/observability-agent-ui:${TAG} -f Dockerfile.new .

# Push the UI container to the registry
echo "Pushing the UI container to the registry..."
docker push ${REGISTRY}/observability-agent-ui:${TAG}

# Restart the UI deployment
echo "Restarting the UI deployment..."
kubectl rollout restart deployment observability-agent-ui -n ${NAMESPACE}

echo "Waiting for the UI deployment to be ready..."
kubectl rollout status deployment observability-agent-ui -n ${NAMESPACE}

echo "UI updated successfully!"
