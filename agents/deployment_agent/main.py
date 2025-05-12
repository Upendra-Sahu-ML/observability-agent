from deploy import DeploymentAgent
import os
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()

    # Initialize the deployment agent with env vars or use defaults
    argocd_server = os.environ.get("ARGOCD_SERVER", "https://argocd-server.argocd:443")
    git_repo_path = os.environ.get("GIT_REPO_PATH", "/app/repo")
    
    agent = DeploymentAgent(argocd_server=argocd_server, git_repo_path=git_repo_path)
    
    print("[DeploymentAgent] Starting deployment agent...")
    # Start listening for messages from orchestrator
    agent.listen()

if __name__ == "__main__":
    main()
