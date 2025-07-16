FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Azure CLI, kubectl, and infrastructure tools
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    lsb-release \
    ca-certificates \
    git \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install Azure CLI
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# Install Helm (for deployment management)
RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy common tools and config (shared across agents)
COPY common/ ./common/

# Copy agent-specific code
COPY agents/infrastructure_agent/ ./agents/infrastructure_agent/

# Set Python path to include common modules
ENV PYTHONPATH="/app:/app/common"

# Set working directory to agent directory
WORKDIR /app/agents/infrastructure_agent

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; import nats; asyncio.run(nats.connect('nats://nats:4222', connect_timeout=5))" || exit 1

# Run the agent
CMD ["python", "main.py"]