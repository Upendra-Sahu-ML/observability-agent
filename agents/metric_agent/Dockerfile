FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt /app/requirements.txt
COPY agents/metric_agent/requirements.txt /app/agents/metric_agent/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN pip install --no-cache-dir -r /app/agents/metric_agent/requirements.txt

# Copy the rest of the application
COPY common/ /app/common/
COPY agents/metric_agent/ /app/agents/metric_agent/

# Set the working directory to the agent directory
WORKDIR /app/agents/metric_agent

# Run the agent
CMD ["python", "main.py"]