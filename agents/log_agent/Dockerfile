FROM python:3.10-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy requirements first for better layer caching
COPY requirements.txt /app/requirements.txt
COPY agents/log_agent/requirements.txt /app/agents/log_agent/requirements.txt


# Install dependencies using uv
RUN uv pip install --system --no-cache -r /app/requirements.txt
RUN uv pip install --system --no-cache -r /app/agents/log_agent/requirements.txt

# Copy the rest of the application
COPY common/ /app/common/
COPY agents/log_agent/ /app/agents/log_agent/

# Set the working directory to the agent directory
WORKDIR /app

# Run the agent
CMD ["python", "agents/log_agent/main.py"]