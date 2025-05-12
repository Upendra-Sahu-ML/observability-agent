"""
Git repository tools for checking code changes
"""
import os
import subprocess
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

class GitFileChangeTool(AgentTool):
    """Tool for checking changes to specific files in a Git repository"""
    
    @property
    def name(self):
        return "git_file_changes"
    
    @property
    def description(self):
        return "Check changes to specific files or directories in a Git repository"
    
    def execute(self, repo_path, path, since=None, max_commits=10):
        """
        Get commits that modified specific files or directories
        
        Args:
            repo_path (str): Path to the Git repository
            path (str): Path to file or directory to check
            since (str, optional): Get commits since this time (e.g., "1 day ago")
            max_commits (int, optional): Maximum number of commits to retrieve
            
        Returns:
            dict: Commit information for files that changed
        """
        if not os.path.exists(os.path.join(repo_path, ".git")):
            return {"error": f"Not a valid Git repository: {repo_path}"}
            
        # Build the git command
        cmd = ["git", "-C", repo_path, "log", f"-{max_commits}", "--pretty=format:%h|%an|%ad|%s", "--date=iso"]
        
        if since:
            cmd.append(f"--since={since}")
            
        # Add path to check
        cmd.append("--")
        cmd.append(path)
            
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
            
            return {"path": path, "commits": commits, "count": len(commits)}
                
        except subprocess.CalledProcessError as e:
            return {"error": str(e), "output": e.output}
    
    def get_file_at_commit(self, repo_path, file_path, commit_hash):
        """
        Get the content of a file at a specific commit
        
        Args:
            repo_path (str): Path to the Git repository
            file_path (str): Path to the file
            commit_hash (str): Hash of the commit
            
        Returns:
            dict: File content at that commit
        """
        if not os.path.exists(os.path.join(repo_path, ".git")):
            return {"error": f"Not a valid Git repository: {repo_path}"}
            
        cmd = ["git", "-C", repo_path, "show", f"{commit_hash}:{file_path}"]
            
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            return {"file": file_path, "commit": commit_hash, "content": output}
                
        except subprocess.CalledProcessError as e:
            return {"error": str(e), "output": e.output}