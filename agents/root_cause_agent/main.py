from root_cause import RootCauseAgent
import os
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    print("[RootCauseAgent] Starting root cause agent...")
    # Initialize the agent
    agent = RootCauseAgent()
    # Start listening for messages from orchestrator
    agent.listen()

if __name__ == "__main__":
    main()
