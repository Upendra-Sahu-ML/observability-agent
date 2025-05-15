FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt /app/requirements.txt
COPY agents/notification_agent/requirements.txt /app/agents/notification_agent/requirements.txt

# Install dependencies
# Install uv
RUN pip install --no-cache-dir uv
RUN uv pip install --system --upgrade pip
RUN uv pip install --system --no-cache-dir -r /app/requirements.txt
RUN uv pip install --system --no-cache-dir -r /app/agents/notification_agent/requirements.txt

# Copy the rest of the application
COPY common/ /app/common/
COPY agents/notification_agent/ /app/agents/notification_agent/

# Set the working directory to the agent directory
WORKDIR /app

# Run the agent
CMD ["python", "agents/notification_agent/main.py"]