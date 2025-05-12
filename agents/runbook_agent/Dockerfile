FROM python:3.10-slim

WORKDIR /app

# Install Rust compiler and cargo for tiktoken if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Add cargo to PATH
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy requirements first for better layer caching
COPY requirements.txt /app/requirements.txt
COPY agents/runbook_agent/requirements.txt /app/agents/runbook_agent/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN pip install --no-cache-dir -r /app/agents/runbook_agent/requirements.txt

# Copy the rest of the application
COPY common/ /app/common/
COPY agents/runbook_agent/ /app/agents/runbook_agent/

# Set the working directory to the agent directory
WORKDIR /app/agents/runbook_agent

# Run the agent
CMD ["python", "main.py"]