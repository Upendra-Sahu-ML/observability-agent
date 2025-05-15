FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt /app/requirements.txt
COPY orchestrator/requirements.txt /app/orchestrator/requirements.txt

# Install uv for faster package installation
RUN pip install --no-cache-dir uv
# Install dependencies using --system flag to install without a virtual environment
RUN uv pip install --system --upgrade pip
RUN uv pip install --system --no-cache-dir -r /app/requirements.txt
RUN uv pip install --system --no-cache-dir -r /app/orchestrator/requirements.txt

# Copy the rest of the application
COPY common/ /app/common/
COPY orchestrator/ /app/orchestrator/

# Set the working directory to the orchestrator directory
WORKDIR /app

# Run the orchestrator
CMD ["python", "orchestrator/main.py"]