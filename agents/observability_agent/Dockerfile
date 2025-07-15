FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy common tools and config (shared across agents)
COPY common/ ./common/

# Copy agent-specific code
COPY agents/observability_agent/ ./agents/observability_agent/

# Set Python path to include common modules
ENV PYTHONPATH="/app:/app/common"

# Set working directory to agent directory
WORKDIR /app/agents/observability_agent

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; import nats; asyncio.run(nats.connect('nats://nats:4222', connect_timeout=5))" || exit 1

# Run the agent
CMD ["python", "main.py"]