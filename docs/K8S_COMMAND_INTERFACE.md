# Kubernetes Command Interface

The Kubernetes Command Interface is a feature of the Observability Agent that allows users to run Kubernetes commands using natural language. It provides a Jupyter notebook-like interface for executing, saving, and sharing Kubernetes commands.

## Features

- **Natural Language to Kubernetes Commands**: Convert natural language queries into kubectl commands using OpenAI's GPT-4 model
- **Jupyter Notebook-like Interface**: Add, remove, and execute commands in a notebook-like interface
- **Command History**: Keep track of executed commands and their outputs
- **Save and Load Notebooks**: Save notebooks for later use and share them with others
- **Export as Runbooks**: Export notebooks as runbooks for incident response
- **Extensible Architecture**: Designed to support other command types in the future (AWS CLI, Prometheus, etc.)

## Architecture

The Kubernetes Command Interface consists of two main components:

1. **K8s Command Backend**: A Node.js backend service that handles:
   - Converting natural language to Kubernetes commands using OpenAI
   - Executing Kubernetes commands
   - Storing notebooks in MongoDB
   - Exporting notebooks as runbooks

2. **K8s Command Frontend**: A React component integrated into the main UI that provides:
   - A notebook-like interface for commands
   - Features to add, remove, and execute commands
   - Functionality to save, load, and export notebooks

## Usage

### Accessing the Interface

1. Navigate to the Observability Agent UI at `http://localhost:8080` (or your deployed URL)
2. Click on the "K8s Commands" link in the navigation bar
3. You will be presented with the Kubernetes Command Interface

### Running Commands

1. Enter a natural language query in the command cell, such as:
   - "List all pods in the kube-system namespace"
   - "Find pods that are not running"
   - "Show me the logs for the nginx pod"
   - "Get all deployments with more than 3 replicas"

2. Click the "Run" button (play icon) to execute the command
3. The command will be converted to a kubectl command and executed
4. The result will be displayed in a result cell below the command

For a comprehensive list of example queries and usage tips, see the [K8s Command Examples](K8S_COMMAND_EXAMPLES.md) documentation.

### Managing Notebooks

1. **Creating a New Notebook**:
   - Click the "New Notebook" button (plus icon) in the toolbar

2. **Saving a Notebook**:
   - Click the "Save" button (save icon) in the toolbar
   - Enter a name and optional description for the notebook
   - Click "Save"

3. **Loading a Notebook**:
   - Click the "Load" button (folder icon) in the toolbar
   - Select a notebook from the list
   - Click on the notebook to load it

4. **Exporting as a Runbook**:
   - Click the "Export" button (download icon) in the toolbar
   - Enter an optional service name for the runbook
   - Click "Export"
   - The notebook will be exported as a runbook and available in the Runbooks section

## API Endpoints

The K8s Command Backend provides the following API endpoints:

- `GET /health` - Health check endpoint
- `POST /api/convert` - Convert natural language to Kubernetes command
- `POST /api/execute` - Execute Kubernetes command
- `GET /api/notebooks` - Get all notebooks
- `GET /api/notebooks/:id` - Get notebook by ID
- `POST /api/notebooks` - Create a new notebook
- `PUT /api/notebooks/:id` - Update a notebook
- `DELETE /api/notebooks/:id` - Delete a notebook
- `POST /api/notebooks/:id/export` - Export notebook as runbook

## Configuration

### Environment Variables

The K8s Command Backend can be configured with the following environment variables:

- `PORT` - Port to listen on (default: 5002)
- `MONGODB_URI` - MongoDB connection URI (default: mongodb://localhost:27017/k8s-command)
- `NATS_URL` - NATS server URL (default: nats://localhost:4222)
- `OPENAI_API_KEY` - OpenAI API key (required)
- `KUBECONFIG` - Path to kubeconfig file (only needed for local development, not required in-cluster)

### Kubernetes RBAC

#### K8s Command Backend RBAC

The K8s Command Backend requires specific permissions to execute Kubernetes commands. The following RBAC resources are created:

1. **ServiceAccount**: `observability-agent-k8s-command-backend`
2. **ClusterRole**: `observability-agent-k8s-command-backend` with permissions to:
   - List, get, and watch pods, deployments, services, etc.
   - Read logs from pods
   - Get information about nodes, namespaces, etc.
3. **ClusterRoleBinding**: Binds the ServiceAccount to the ClusterRole

#### Runbook Agent RBAC

The Runbook Agent also requires permissions to execute Kubernetes commands when running runbooks. Similar RBAC resources are created:

1. **ServiceAccount**: `observability-agent-runbook-agent`
2. **ClusterRole**: `observability-agent-runbook-agent` with the same permissions as the K8s Command Backend
3. **ClusterRoleBinding**: Binds the ServiceAccount to the ClusterRole

These RBAC resources are automatically created when deploying the Helm chart.

## Deployment

### Local Development

1. Start MongoDB:
   ```bash
   docker run -d -p 27017:27017 --name mongodb mongo:6.0
   ```

2. Start the K8s Command Backend:
   ```bash
   cd ui/k8s-command-backend
   npm install
   OPENAI_API_KEY=your_api_key KUBECONFIG=~/.kube/config npm start
   ```

   > **Note**: For local development, you need to provide the `KUBECONFIG` environment variable pointing to your local kubeconfig file. This is not needed when running in a Kubernetes cluster, as the service account will automatically provide access to the Kubernetes API.

3. Start the UI:
   ```bash
   cd ui
   npm install
   npm start
   ```

### Docker Compose

The K8s Command Backend and MongoDB are included in the docker-compose.yaml file:

```bash
docker-compose up -d
```

### Kubernetes Deployment

The K8s Command Backend is included in the Helm chart:

```bash
make deploy
```

When deployed in a Kubernetes cluster, the K8s Command Backend uses a service account with appropriate RBAC permissions to access the Kubernetes API. No additional configuration is needed for Kubernetes access.

## Future Enhancements

1. **Support for Other Command Types**:
   - AWS CLI commands
   - Prometheus queries
   - Other cloud provider CLI tools

2. **Enhanced Notebook Features**:
   - Version history for notebooks
   - Collaboration features
   - More export formats

3. **Security Enhancements**:
   - Role-based access control
   - Command validation and sanitization
   - Audit logging

## Troubleshooting

### Common Issues

1. **OpenAI API Key Not Set**:
   - Ensure the OPENAI_API_KEY environment variable is set
   - Check the logs for API key errors

2. **MongoDB Connection Issues**:
   - Verify MongoDB is running
   - Check the MONGODB_URI environment variable
   - Look for connection errors in the logs

3. **Command Execution Failures**:
   - For local development:
     - Ensure kubectl is installed and configured
     - Check that the KUBECONFIG environment variable is set correctly
     - Verify your local kubeconfig has the necessary permissions
   - For in-cluster deployment:
     - Verify the service account has the necessary RBAC permissions
     - Check the logs for permission errors
     - Ensure the cluster is healthy

### Logs

- K8s Command Backend logs: `kubectl logs deployment/observability-agent-k8s-command-backend`
- MongoDB logs: `kubectl logs deployment/observability-agent-mongodb`

## Support

For issues or feature requests, please contact the Observability Agent team or open an issue on GitHub.
