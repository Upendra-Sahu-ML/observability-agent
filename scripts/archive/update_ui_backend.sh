#!/bin/bash
# Script to update the UI backend in the Kubernetes cluster
# This script copies the fixed files to the UI backend pod and restarts it

# Set the namespace
NAMESPACE="observability"

# Get the UI backend pod name
UI_BACKEND_POD=$(kubectl get pods -n $NAMESPACE | grep ui-backend | awk '{print $1}')
echo "Found UI backend pod: $UI_BACKEND_POD"

if [ -z "$UI_BACKEND_POD" ]; then
  echo "Error: UI backend pod not found"
  exit 1
fi

echo "Found UI backend pod: $UI_BACKEND_POD"

# Copy the fixed files to the pod
echo "Copying fixed server.js to the pod..."
kubectl cp ../ui/backend/server.js $NAMESPACE/$UI_BACKEND_POD:/app/server.js

echo "Copying fixed knowledge.js to the pod..."
kubectl cp ../ui/backend/knowledge.js $NAMESPACE/$UI_BACKEND_POD:/app/knowledge.js

# Restart the pod
echo "Restarting the UI backend pod..."
kubectl delete pod -n $NAMESPACE $UI_BACKEND_POD

echo "Waiting for the new pod to start..."
sleep 5

# Wait for the new pod to be created
sleep 10

# Get the new pod name
NEW_UI_BACKEND_POD=$(kubectl get pods -n $NAMESPACE | grep ui-backend | awk '{print $1}')

echo "New UI backend pod: $NEW_UI_BACKEND_POD"

# Wait for the pod to be ready
echo "Waiting for the pod to be ready..."
if [ -n "$NEW_UI_BACKEND_POD" ]; then
  kubectl wait --for=condition=ready pod -n $NAMESPACE $NEW_UI_BACKEND_POD --timeout=60s
else
  echo "Warning: Could not find new pod, skipping wait"
  sleep 30
fi

echo "UI backend updated successfully!"
