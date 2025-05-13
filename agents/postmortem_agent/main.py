import asyncio
from postmortem import PostmortemAgent
import os
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()

    # Initialize the postmortem agent with configuration from env vars or use defaults
    template_dir = os.environ.get("TEMPLATE_DIR", "/app/templates")
    nats_server = os.environ.get("NATS_URL", "nats://nats:4222")
    
    agent = PostmortemAgent(template_dir=template_dir, nats_server=nats_server)
    
    print("[PostmortemAgent] Starting postmortem agent...")
    
    # Run the async listen method in the event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(agent.listen())
    except KeyboardInterrupt:
        print("[PostmortemAgent] Shutting down...")
    finally:
        if agent.nats_client and agent.nats_client.is_connected:
            loop.run_until_complete(agent.nats_client.close())
        loop.close()

if __name__ == "__main__":
    main()