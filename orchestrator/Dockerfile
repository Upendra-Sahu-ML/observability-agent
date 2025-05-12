FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt /app/requirements.txt
COPY orchestrator/requirements.txt /app/orchestrator/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN pip install --no-cache-dir -r /app/orchestrator/requirements.txt

# Copy the rest of the application
COPY common/ /app/common/
COPY orchestrator/ /app/orchestrator/

# Set the working directory to the orchestrator directory
WORKDIR /app/orchestrator

# Run the orchestrator
CMD ["python", "main.py"]