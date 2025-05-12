from runbook import RunbookAgent
import os
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize the runbook agent with env vars or use defaults
    redis_host = os.environ.get("REDIS_HOST", "redis")
    redis_port = int(os.environ.get("REDIS_PORT", 6379))
    openai_model = os.environ.get("OPENAI_MODEL", "gpt-4")
    runbook_base_url = os.environ.get("RUNBOOK_BASE_URL", "http://runbooks-service:8080")
    
    agent = RunbookAgent(
        redis_host=redis_host,
        redis_port=redis_port,
        openai_model=openai_model,
        runbook_base_url=runbook_base_url
    )
    
    print("[RunbookAgent] Starting runbook agent...")
    # Start listening for messages from the root cause agent
    agent.listen()

if __name__ == "__main__":
    main()