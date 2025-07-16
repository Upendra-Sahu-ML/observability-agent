FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project (for common modules)
COPY . .

# Set the working directory to the agent
WORKDIR /app/agents/communication_agent

# Run the agent
CMD ["python", "agent.py"]