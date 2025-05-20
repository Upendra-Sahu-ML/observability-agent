# Kubernetes Command Interface - User Guide

This guide provides examples and instructions for using the Kubernetes Command Interface in the Observability Agent.

## Getting Started

The Kubernetes Command Interface allows you to run Kubernetes commands using natural language. It converts your natural language queries into kubectl commands and executes them, displaying the results in a notebook-like interface.

### Accessing the Interface

1. Navigate to the Observability Agent UI
2. Click on the "K8s Commands" link in the navigation bar
3. You will be presented with the Kubernetes Command Interface

## Basic Usage

1. Enter a natural language query in the command cell
2. Click the "Run" button (play icon) to execute the command
3. The command will be converted to a kubectl command and executed
4. The result will be displayed in a result cell below the command

## Example Queries

Here are examples of natural language queries you can use with the Kubernetes Command Interface:

### Listing Resources

| Natural Language Query | Equivalent kubectl Command |
|------------------------|----------------------------|
| List all pods in the default namespace | `kubectl get pods -n default` |
| Show all namespaces | `kubectl get namespaces` |
| Get all deployments in the kube-system namespace | `kubectl get deployments -n kube-system` |
| Show me all services across all namespaces | `kubectl get services --all-namespaces` |
| List all pods with their IP addresses | `kubectl get pods -o wide` |
| Find all pods with the app=nginx label | `kubectl get pods -l app=nginx` |
| Show all nodes in the cluster | `kubectl get nodes` |
| List all persistent volume claims | `kubectl get pvc` |
| Get all config maps in the monitoring namespace | `kubectl get configmaps -n monitoring` |
| Show all secrets in the default namespace | `kubectl get secrets` |

### Describing Resources

| Natural Language Query | Equivalent kubectl Command |
|------------------------|----------------------------|
| Describe the nginx pod | `kubectl describe pod nginx` |
| Get details about the default-token secret | `kubectl describe secret default-token` |
| Show me information about the kube-system namespace | `kubectl describe namespace kube-system` |
| Describe the nginx deployment | `kubectl describe deployment nginx` |
| Get detailed information about the node worker-1 | `kubectl describe node worker-1` |
| Tell me about the service called frontend | `kubectl describe service frontend` |
| Describe the persistent volume claim data-pvc | `kubectl describe pvc data-pvc` |
| Get details of the configmap app-config | `kubectl describe configmap app-config` |
| Show information about the ingress main-ingress | `kubectl describe ingress main-ingress` |
| Describe the statefulset mongodb | `kubectl describe statefulset mongodb` |

### Viewing Logs

| Natural Language Query | Equivalent kubectl Command |
|------------------------|----------------------------|
| Show logs for the nginx pod | `kubectl logs nginx` |
| Get the last 100 lines of logs from the api-server pod | `kubectl logs api-server --tail=100` |
| Show logs for the container auth in the pod gateway | `kubectl logs gateway -c auth` |
| Display logs from all pods with the label app=backend | `kubectl logs -l app=backend` |
| Show logs from the previous instance of the pod worker | `kubectl logs worker --previous` |
| Get logs from the nginx pod in the production namespace | `kubectl logs nginx -n production` |
| Show logs from the last hour for the database pod | `kubectl logs database --since=1h` |
| Display logs and follow new entries for the api pod | `kubectl logs api -f` |
| Show logs with timestamps for the cache pod | `kubectl logs cache --timestamps` |
| Get logs from all containers in the pod gateway | `kubectl logs gateway --all-containers` |

### Filtering and Sorting

| Natural Language Query | Equivalent kubectl Command |
|------------------------|----------------------------|
| Find pods that are not running | `kubectl get pods --field-selector status.phase!=Running` |
| List pods sorted by creation time | `kubectl get pods --sort-by=.metadata.creationTimestamp` |
| Show pods with high restart counts | `kubectl get pods --sort-by='.status.containerStatuses[0].restartCount'` |
| Find pods with more than 500Mi of memory requests | `kubectl get pods -o json | jq '.items[] | select(.spec.containers[].resources.requests.memory | tonumber > 500)'` |
| List all pods that have been running for more than 7 days | `kubectl get pods --field-selector status.phase=Running --sort-by=.metadata.creationTimestamp` |
| Show nodes with their CPU and memory capacity | `kubectl get nodes -o custom-columns=NAME:.metadata.name,CPU:.status.capacity.cpu,MEMORY:.status.capacity.memory` |
| Find pods that have the annotation "critical=true" | `kubectl get pods -o json | jq '.items[] | select(.metadata.annotations."critical" == "true")'` |
| List deployments with less than desired replicas | `kubectl get deployments -o json | jq '.items[] | select(.status.replicas < .spec.replicas)'` |
| Show pods that are using the hostNetwork | `kubectl get pods -o json | jq '.items[] | select(.spec.hostNetwork == true)'` |
| Find pods scheduled on node worker-1 | `kubectl get pods --field-selector spec.nodeName=worker-1` |

### Advanced Queries

| Natural Language Query | Equivalent kubectl Command |
|------------------------|----------------------------|
| Show the CPU and memory usage of all pods | `kubectl top pods` |
| Get the resource usage of all nodes | `kubectl top nodes` |
| Show all events in the cluster | `kubectl get events --sort-by=.metadata.creationTimestamp` |
| List all API resources available in the cluster | `kubectl api-resources` |
| Show the YAML definition of the nginx deployment | `kubectl get deployment nginx -o yaml` |
| Find all pods that have liveness probes configured | `kubectl get pods -o json | jq '.items[] | select(.spec.containers[].livenessProbe != null)'` |
| Show all pods that have environment variables containing DATABASE | `kubectl get pods -o json | jq '.items[].spec.containers[].env[] | select(.name | contains("DATABASE"))'` |
| List all pods that use hostPath volumes | `kubectl get pods -o json | jq '.items[] | select(.spec.volumes[].hostPath != null)'` |
| Show all pods that have init containers | `kubectl get pods -o json | jq '.items[] | select(.spec.initContainers != null)'` |
| Find all services that expose port 80 | `kubectl get services -o json | jq '.items[] | select(.spec.ports[].port == 80)'` |

## Tips and Tricks

1. **Be Specific**: The more specific your query, the more accurate the generated command will be.
   - Good: "List all pods in the kube-system namespace with the label app=monitoring"
   - Less Good: "Show me the pods"

2. **Use Natural Language**: You don't need to know kubectl syntax. Just describe what you want to see.
   - Example: "Show me all pods that are not running" instead of remembering field selectors

3. **Combine Multiple Criteria**: You can combine multiple criteria in a single query.
   - Example: "Find pods in the production namespace that have more than 3 restarts"

4. **Ask for Specific Output Formats**: You can request specific output formats.
   - Example: "Show the YAML definition of the nginx deployment"
   - Example: "Display pods in wide format with IP addresses"

5. **Use Follow-up Commands**: You can reference previous results in follow-up commands.
   - Example: After listing pods, you can say "Show logs for the first pod in the list"

## Managing Notebooks

### Creating a New Notebook

1. Click the "New Notebook" button (plus icon) in the toolbar
2. This will create a new, empty notebook with a single command cell

### Saving a Notebook

1. Click the "Save" button (save icon) in the toolbar
2. Enter a name and optional description for the notebook
3. Click "Save"

### Loading a Notebook

1. Click the "Load" button (folder icon) in the toolbar
2. Select a notebook from the list
3. Click on the notebook to load it

### Exporting as a Runbook

1. Click the "Export" button (download icon) in the toolbar
2. Enter an optional service name for the runbook
3. Click "Export"
4. The notebook will be exported as a runbook and available in the Runbooks section

## Troubleshooting

### Common Issues

1. **Command Not Found**: If you see "command not found" errors, it might be because:
   - The kubectl command is not installed on the server
   - The service account doesn't have the necessary permissions

2. **Permission Denied**: If you see "permission denied" errors, it might be because:
   - The service account doesn't have the necessary RBAC permissions
   - The resource you're trying to access is in a namespace you don't have access to

3. **Resource Not Found**: If you see "not found" errors, it might be because:
   - The resource doesn't exist
   - You're looking in the wrong namespace
   - There's a typo in the resource name

### Getting Help

If you encounter issues with the Kubernetes Command Interface, try:

1. Checking the logs of the k8s-command-backend pod
2. Verifying that the service account has the necessary permissions
3. Ensuring that the Kubernetes cluster is accessible from the pod

## Advanced Features

### Adding Custom Commands

You can add custom commands to your notebooks by directly editing the generated kubectl command before execution.

1. Enter a natural language query
2. The system will convert it to a kubectl command
3. Edit the command if needed
4. Click the "Run" button to execute the modified command

### Creating Command Templates

You can create command templates by saving notebooks with common queries:

1. Create a new notebook
2. Add common queries you use frequently
3. Save the notebook with a descriptive name like "Common Monitoring Commands"
4. Load this notebook whenever you need to run these commands

### Combining with Runbooks

You can use the Kubernetes Command Interface to create runbooks for incident response:

1. Create a notebook with commands for diagnosing and fixing common issues
2. Add descriptive text between commands to explain the troubleshooting process
3. Export the notebook as a runbook
4. Share the runbook with your team
