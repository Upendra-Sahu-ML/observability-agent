#!/bin/bash
# Script to build and deploy the updated UI backend

# Set variables
REGISTRY=${REGISTRY:-docker.io/upendrasahu}
TAG=${TAG:-latest}
IMAGE_NAME=observability-agent-ui-backend

# We've directly updated the server.js and Dockerfile files
echo "Using updated server.js and Dockerfile..."

# Build the Docker image
echo "Building Docker image ${REGISTRY}/${IMAGE_NAME}:${TAG}..."
docker build -t ${REGISTRY}/${IMAGE_NAME}:${TAG} ui/backend

# Push the Docker image
echo "Pushing Docker image ${REGISTRY}/${IMAGE_NAME}:${TAG}..."
docker push ${REGISTRY}/${IMAGE_NAME}:${TAG}

# Update the deployment
echo "Updating the UI backend deployment..."
kubectl set image deployment/observability-agent-ui-backend ui-backend=${REGISTRY}/${IMAGE_NAME}:${TAG} -n observability

# Restart the deployment
echo "Restarting the UI backend deployment..."
kubectl rollout restart deployment/observability-agent-ui-backend -n observability

# Wait for the deployment to be ready
echo "Waiting for the deployment to be ready..."
kubectl rollout status deployment/observability-agent-ui-backend -n observability

echo "Deployment complete!"
