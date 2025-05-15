FROM python:3.10-slim

WORKDIR /app

# Install Rust compiler and cargo for tiktoken if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Add cargo to PATH
ENV PATH="/root/.cargo/bin:${PATH}"

# Install uv for faster package installation
RUN pip install --no-cache-dir uv

# Copy requirements first for better layer caching
COPY requirements.txt /app/requirements.txt
COPY agents/deployment_agent/requirements.txt /app/agents/deployment_agent/requirements.txt

# Install dependencies using uv with --system flag to install without a virtual environment
RUN uv pip install --system --upgrade pip
RUN uv pip install --system --no-cache-dir -r /app/requirements.txt
RUN uv pip install --system --no-cache-dir -r /app/agents/deployment_agent/requirements.txt

# Copy the rest of the application
COPY common/ /app/common/
COPY agents/deployment_agent/ /app/agents/deployment_agent/

# Set the working directory to the agent directory
WORKDIR /app/

# Run the agent
CMD ["python", "agents/deployment_agent/main.py"]