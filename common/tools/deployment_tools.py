"""
Deployment tools for checking Git repositories and ArgoCD deployment history
"""
import os
import json
import subprocess
import requests
from datetime import datetime, timedelta
from urllib.parse import urljoin
from common.tools.base import AgentTool

class GitChangeTool(AgentTool):
    """Tool for checking recent Git repository changes"""
    
    @property
    def name(self):
        return "git_changes"
    
    @property
    def description(self):
        return "Check recent changes in a Git repository"
    
    def execute(self, repo_path, branch="main", since=None, author=None, max_commits=10):
        """
        Get recent commits from a Git repository
        
        Args:
            repo_path (str): Path to the Git repository
            branch (str, optional): Branch to check (default: main)
            since (str, optional): Get commits since this time (e.g., "1 day ago", "2.weeks", "yesterday")
            author (str, optional): Filter commits by author
            max_commits (int, optional): Maximum number of commits to retrieve
            
        Returns:
            dict: Recent commit information
        """
        if not os.path.exists(os.path.join(repo_path, ".git")):
            return {"error": f"Not a valid Git repository: {repo_path}"}
            
        # Build the git command
        cmd = ["git", "-C", repo_path, "log", f"-{max_commits}", "--pretty=format:%h|%an|%ad|%s", "--date=iso"]
        
        if branch:
            cmd.append(branch)
            
        if since:
            cmd.append(f"--since={since}")
            
        if author:
            cmd.append(f"--author={author}")
            
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            commits = []
            
            for line in output.splitlines():
                if not line.strip():
                    continue
                    
                parts = line.split("|", 3)
                if len(parts) >= 4:
                    commit = {
                        "hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3]
                    }
                    commits.append(commit)
            
            return {"commits": commits, "count": len(commits)}
                
        except subprocess.CalledProcessError as e:
            return {"error": str(e), "output": e.output}
    
    def get_diff(self, repo_path, commit_hash, previous_hash=None):
        """
        Get the diff for a specific commit
        
        Args:
            repo_path (str): Path to the Git repository
            commit_hash (str): Hash of the commit to get diff for
            previous_hash (str, optional): Compare with this commit instead of the parent
            
        Returns:
            dict: Commit diff information
        """
        if not os.path.exists(os.path.join(repo_path, ".git")):
            return {"error": f"Not a valid Git repository: {repo_path}"}
            
        # Build the git command
        if previous_hash:
            cmd = ["git", "-C", repo_path, "diff", f"{previous_hash}..{commit_hash}"]
        else:
            cmd = ["git", "-C", repo_path, "show", commit_hash]
            
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            return {"diff": output}
                
        except subprocess.CalledProcessError as e:
            return {"error": str(e), "output": e.output}

class ArgoCDTool(AgentTool):
    """Tool for interacting with ArgoCD to check deployment history"""
    
    def __init__(self, argocd_server="https://argocd-server.argocd:443", api_token=None):
        self.base_url = argocd_server
        self.api_path = "/api/v1/"
        self.api_token = api_token or os.environ.get("ARGOCD_TOKEN")
        
        if not self.api_token:
            raise ValueError("ArgoCD API token is required. Provide it or set ARGOCD_TOKEN environment variable.")
    
    @property
    def name(self):
        return "argocd_history"
    
    @property
    def description(self):
        return "Check ArgoCD application deployment history"
    
    def execute(self, app_name, limit=10):
        """
        Get deployment history for an ArgoCD application
        
        Args:
            app_name (str): Name of the ArgoCD application
            limit (int, optional): Maximum number of history entries to retrieve
            
        Returns:
            dict: Application deployment history
        """
        endpoint = urljoin(self.base_url, f"{self.api_path}applications/{app_name}/rollout")
        headers = {"Authorization": f"Bearer {self.api_token}"}
        
        params = {"limit": limit}
            
        response = requests.get(endpoint, headers=headers, params=params, verify=False)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"ArgoCD API request failed with status {response.status_code}", "details": response.text}
    
    def get_application_status(self, app_name):
        """
        Get current status of an ArgoCD application
        
        Args:
            app_name (str): Name of the ArgoCD application
            
        Returns:
            dict: Application status information
        """
        endpoint = urljoin(self.base_url, f"{self.api_path}applications/{app_name}")
        headers = {"Authorization": f"Bearer {self.api_token}"}
            
        response = requests.get(endpoint, headers=headers, verify=False)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"ArgoCD API request failed with status {response.status_code}", "details": response.text}

class KubeDeploymentTool(AgentTool):
    """Tool for checking Kubernetes deployment status and history"""
    
    @property
    def name(self):
        return "kube_deployment"
    
    @property
    def description(self):
        return "Check Kubernetes deployment status and revision history"
    
    def execute(self, namespace, deployment_name):
        """
        Get information about a Kubernetes deployment including revision history
        
        Args:
            namespace (str): Kubernetes namespace
            deployment_name (str): Name of the deployment
            
        Returns:
            dict: Deployment status and history information
        """
        # Get deployment details
        cmd_deployment = ["kubectl", "get", "deployment", deployment_name, "-n", namespace, "-o", "json"]
        
        # Get rollout history
        cmd_history = ["kubectl", "rollout", "history", "deployment", deployment_name, "-n", namespace]
        
        result = {}
        
        try:
            # Get deployment details
            deployment_output = subprocess.check_output(cmd_deployment, stderr=subprocess.STDOUT, universal_newlines=True)
            result["deployment"] = json.loads(deployment_output)
                
        except subprocess.CalledProcessError as e:
            result["deployment_error"] = {"error": str(e), "output": e.output}
            
        try:
            # Get rollout history
            history_output = subprocess.check_output(cmd_history, stderr=subprocess.STDOUT, universal_newlines=True)
            
            # Parse the history output
            history_lines = history_output.splitlines()
            headers = None
            revisions = []
            
            for line in history_lines:
                if line.startswith("REVISION"):
                    headers = line.split()
                elif headers and line.strip():
                    revision_info = {}
                    parts = line.split()
                    
                    if len(parts) >= len(headers):
                        for i, header in enumerate(headers):
                            revision_info[header.lower()] = parts[i]
                        revisions.append(revision_info)
            
            result["history"] = revisions
                
        except subprocess.CalledProcessError as e:
            result["history_error"] = {"error": str(e), "output": e.output}
            
        return result