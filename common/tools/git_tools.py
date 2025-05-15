"""
Git repository tools for checking code changes
"""
import os
import subprocess
from typing import Dict, Any, Optional
from crewai.tools import tool

class GitTools:
    """Tools for working with Git repositories"""
    
    @tool("Check recent changes in a Git repository")
    def get_recent_commits(self, repo_path: str, branch: str = "main", since: Optional[str] = None, 
                        author: Optional[str] = None, max_commits: int = 10) -> Dict[str, Any]:
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
    
    @tool("Get the diff for a specific commit")
    def get_commit_diff(self, repo_path: str, commit_hash: str, previous_hash: Optional[str] = None) -> Dict[str, Any]:
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

    @tool("Check changes to specific files or directories in a Git repository")
    def get_file_history(self, repo_path: str, path: str, since: Optional[str] = None, max_commits: int = 10) -> Dict[str, Any]:
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
    
    @tool("Get the content of a file at a specific commit")
    def get_file_at_commit(self, repo_path: str, file_path: str, commit_hash: str) -> Dict[str, Any]:
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
    
    @tool("Get the list of modified files in the working directory")
    def get_modified_files(self, repo_path: str, staged_only: bool = False) -> Dict[str, Any]:
        """
        Get the list of modified files in the working directory
        
        Args:
            repo_path (str): Path to the Git repository
            staged_only (bool, optional): Only return staged files
            
        Returns:
            dict: List of modified files
        """
        if not os.path.exists(os.path.join(repo_path, ".git")):
            return {"error": f"Not a valid Git repository: {repo_path}"}
            
        # Build the git command
        if staged_only:
            cmd = ["git", "-C", repo_path, "diff", "--name-status", "--staged"]
        else:
            cmd = ["git", "-C", repo_path, "status", "--porcelain"]
            
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            files = []
            
            for line in output.splitlines():
                if not line.strip():
                    continue
                
                if staged_only:
                    status, file_path = line.split(maxsplit=1)
                    files.append({"status": status, "file": file_path})
                else:
                    # Parse porcelain output
                    if len(line) >= 4:  # Minimum X  filename
                        status = line[:2].strip()
                        file_path = line[3:].strip()
                        files.append({"status": status, "file": file_path})
            
            return {"files": files, "count": len(files)}
                
        except subprocess.CalledProcessError as e:
            return {"error": str(e), "output": e.output}
    
    @tool("Get the branches in a Git repository")
    def get_branches(self, repo_path: str) -> Dict[str, Any]:
        """
        Get the list of branches in a Git repository
        
        Args:
            repo_path (str): Path to the Git repository
            
        Returns:
            dict: List of branches and the current branch
        """
        if not os.path.exists(os.path.join(repo_path, ".git")):
            return {"error": f"Not a valid Git repository: {repo_path}"}
            
        cmd = ["git", "-C", repo_path, "branch"]
            
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            branches = []
            current_branch = None
            
            for line in output.splitlines():
                branch_name = line.strip()
                
                if branch_name.startswith("* "):
                    # This is the current branch
                    branch_name = branch_name[2:]
                    current_branch = branch_name
                
                if branch_name:
                    branches.append(branch_name)
            
            return {
                "branches": branches, 
                "count": len(branches),
                "current_branch": current_branch
            }
                
        except subprocess.CalledProcessError as e:
            return {"error": str(e), "output": e.output}