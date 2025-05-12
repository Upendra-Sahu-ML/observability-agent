from postmortem import PostmortemAgent
import os
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize the postmortem agent with env vars or use defaults
    redis_host = os.environ.get("REDIS_HOST", "redis")
    redis_port = int(os.environ.get("REDIS_PORT", 6379))
    
    agent = PostmortemAgent(redis_host=redis_host, redis_port=redis_port)
    
    print("[PostmortemAgent] Starting postmortem agent...")
    # Start listening for postmortem requests
    agent.listen()

if __name__ == "__main__":
    main() 