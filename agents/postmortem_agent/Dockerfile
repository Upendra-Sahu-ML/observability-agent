FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt /app/requirements.txt
COPY agents/postmortem_agent/requirements.txt /app/agents/postmortem_agent/requirements.txt

# Install uv
RUN pip install --no-cache-dir uv
# Install dependencies
RUN uv pip install --system --upgrade pip
RUN uv pip install --system --no-cache-dir -r /app/requirements.txt
RUN uv pip install --system --no-cache-dir -r /app/agents/postmortem_agent/requirements.txt

# Copy the rest of the application
COPY common/ /app/common/
COPY agents/postmortem_agent/ /app/agents/postmortem_agent/

# Set the working directory to the agent directory
WORKDIR /app

# Run the agent
CMD ["python", "agents/postmortem_agent/main.py"]