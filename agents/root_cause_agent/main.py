import asyncio
from root_cause import RootCauseAgent
import os
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize the root cause agent with env vars or use defaults
    nats_server = os.environ.get("NATS_URL", "nats://nats:4222")
    
    agent = RootCauseAgent(nats_server=nats_server)
    
    print("[RootCauseAgent] Starting root cause agent...")
    
    # Run the async listen method in the event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(agent.listen())
    except KeyboardInterrupt:
        print("[RootCauseAgent] Shutting down...")
    finally:
        if agent.nats_client and agent.nats_client.is_connected:
            loop.run_until_complete(agent.nats_client.close())
        loop.close()

if __name__ == "__main__":
    main()
