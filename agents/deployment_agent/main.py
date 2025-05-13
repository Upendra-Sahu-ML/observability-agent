import asyncio
from deploy import DeploymentAgent
import os
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()

    # Initialize the deployment agent with configuration from env vars or use defaults
    argocd_server = os.environ.get("ARGOCD_SERVER", "https://argocd-server.argocd:443")
    git_repo_path = os.environ.get("GIT_REPO_PATH", "/app/repo")
    nats_server = os.environ.get("NATS_URL", "nats://nats:4222")
    
    agent = DeploymentAgent(
        argocd_server=argocd_server,
        git_repo_path=git_repo_path,
        nats_server=nats_server
    )
    
    print("[DeploymentAgent] Starting deployment agent...")
    
    # Run the async listen method in the event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(agent.listen())
    except KeyboardInterrupt:
        print("[DeploymentAgent] Shutting down...")
    finally:
        if agent.nats_client and agent.nats_client.is_connected:
            loop.run_until_complete(agent.nats_client.close())
        loop.close()

if __name__ == "__main__":
    main()
