import asyncio
from runbook import RunbookAgent
import os
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize the runbook agent with env vars or use defaults
    nats_server = os.environ.get("NATS_URL", "nats://nats:4222")
    
    agent = RunbookAgent(nats_server=nats_server)
    
    print("[RunbookAgent] Starting runbook agent...")
    
    # Run the async listen method in the event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(agent.listen())
    except KeyboardInterrupt:
        print("[RunbookAgent] Shutting down...")
    finally:
        if agent.nats_client and agent.nats_client.is_connected:
            loop.run_until_complete(agent.nats_client.close())
        loop.close()

if __name__ == "__main__":
    main()