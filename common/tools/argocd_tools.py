"""
ArgoCD tools for querying application deployment status
"""
import os
import logging
import requests
from typing import Dict, Any, Optional, List
from crewai.tools import tool

# Configure logging
logger = logging.getLogger(__name__)

class ArgoCDTools:
    """Tools for interacting with ArgoCD"""
    
    def __init__(self, argocd_api_url=None, argocd_token=None):
        """
        Initialize ArgoCD client
        
        Args:
            argocd_api_url (str, optional): ArgoCD API URL
            argocd_token (str, optional): ArgoCD API token
        """
        self.argocd_api_url = argocd_api_url or os.environ.get('ARGOCD_API_URL')
        self.argocd_token = argocd_token or os.environ.get('ARGOCD_API_TOKEN')
        
        if not self.argocd_api_url:
            logger.warning("ArgoCD API URL not provided, using default: http://argocd-server.argocd.svc.cluster.local")
            self.argocd_api_url = "http://argocd-server.argocd.svc.cluster.local"
            
        if not self.argocd_token:
            logger.warning("ArgoCD API token not provided, authentication might fail")
    
    def _get_headers(self):
        """Get request headers with authentication if token is available"""
        headers = {}
        if self.argocd_token:
            headers["Authorization"] = f"Bearer {self.argocd_token}"
        return headers
    
    @tool("Get information about ArgoCD applications")
    def get_application(self, application_name: Optional[str] = None, application_namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about ArgoCD applications
        
        Args:
            application_name (str, optional): Name of the application
            application_namespace (str, optional): Namespace of the application
            
        Returns:
            dict: Information about the ArgoCD application(s)
        """
        headers = self._get_headers()
        
        try:
            if application_name:
                # Get a specific application
                url = f"{self.argocd_api_url}/api/v1/applications/{application_name}"
                response = requests.get(url, headers=headers, verify=False)
                response.raise_for_status()
                application = response.json()
                applications = [application]
            else:
                # Get all applications
                url = f"{self.argocd_api_url}/api/v1/applications"
                if application_namespace:
                    url += f"?namespace={application_namespace}"
                response = requests.get(url, headers=headers, verify=False)
                response.raise_for_status()
                applications = response.json().get("items", [])
            
            result = {
                "application_count": len(applications),
                "applications": []
            }
            
            for app in applications:
                app_info = {
                    "name": app.get("metadata", {}).get("name"),
                    "namespace": app.get("metadata", {}).get("namespace"),
                    "project": app.get("spec", {}).get("project"),
                    "sync_status": app.get("status", {}).get("sync", {}).get("status"),
                    "health_status": app.get("status", {}).get("health", {}).get("status"),
                    "source": {
                        "repo_url": app.get("spec", {}).get("source", {}).get("repoURL"),
                        "path": app.get("spec", {}).get("source", {}).get("path"),
                        "target_revision": app.get("spec", {}).get("source", {}).get("targetRevision")
                    },
                    "destination": {
                        "server": app.get("spec", {}).get("destination", {}).get("server"),
                        "namespace": app.get("spec", {}).get("destination", {}).get("namespace")
                    },
                    "operation_state": app.get("status", {}).get("operationState", {}).get("phase"),
                    "conditions": app.get("status", {}).get("conditions", [])
                }
                
                result["applications"].append(app_info)
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting ArgoCD application information: {str(e)}")
            return {"error": str(e)}
    
    @tool("Get the resource tree for an ArgoCD application")
    def get_application_resource_tree(self, application_name: str) -> Dict[str, Any]:
        """
        Get the resource tree for an ArgoCD application
        
        Args:
            application_name (str): Name of the application
            
        Returns:
            dict: Resource tree of the application
        """
        headers = self._get_headers()
        
        try:
            url = f"{self.argocd_api_url}/api/v1/applications/{application_name}/resource-tree"
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            resource_tree = response.json()
            
            # Process and structure the resource tree
            result = {
                "application": application_name,
                "nodes": [],
                "pod_count": 0,
                "deployment_count": 0,
                "service_count": 0,
                "configmap_count": 0,
                "secret_count": 0
            }
            
            for node in resource_tree.get("nodes", []):
                node_info = {
                    "kind": node.get("kind"),
                    "name": node.get("name"),
                    "namespace": node.get("namespace"),
                    "group": node.get("group"),
                    "version": node.get("version"),
                    "status": node.get("health", {}).get("status"),
                    "created_at": node.get("createdAt"),
                }
                
                # Increment counter for each resource type
                kind = node.get("kind", "").lower()
                if kind == "pod":
                    result["pod_count"] += 1
                elif kind == "deployment":
                    result["deployment_count"] += 1
                elif kind == "service":
                    result["service_count"] += 1
                elif kind == "configmap":
                    result["configmap_count"] += 1
                elif kind == "secret":
                    result["secret_count"] += 1
                
                result["nodes"].append(node_info)
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting ArgoCD application resource tree: {str(e)}")
            return {"error": str(e)}
    
    @tool("Get events for an ArgoCD application")
    def get_application_events(self, application_name: str) -> Dict[str, Any]:
        """
        Get events for an ArgoCD application
        
        Args:
            application_name (str): Name of the application
            
        Returns:
            dict: Events for the application
        """
        headers = self._get_headers()
        
        try:
            url = f"{self.argocd_api_url}/api/v1/applications/{application_name}/events"
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            events = response.json()
            
            result = {
                "application": application_name,
                "event_count": len(events.get("items", [])),
                "events": []
            }
            
            for event in events.get("items", []):
                event_info = {
                    "reason": event.get("reason"),
                    "message": event.get("message"),
                    "last_timestamp": event.get("lastTimestamp"),
                    "type": event.get("type"),
                    "count": event.get("count")
                }
                
                result["events"].append(event_info)
            
            # Sort events by timestamp (newest first)
            result["events"].sort(key=lambda x: x.get("last_timestamp", ""), reverse=True)
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting ArgoCD application events: {str(e)}")
            return {"error": str(e)}
    
    @tool("Get information about ArgoCD projects")
    def get_project(self, project_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about ArgoCD projects
        
        Args:
            project_name (str, optional): Name of the project
            
        Returns:
            dict: Information about the ArgoCD project(s)
        """
        headers = self._get_headers()
        
        try:
            if project_name:
                # Get a specific project
                url = f"{self.argocd_api_url}/api/v1/projects/{project_name}"
                response = requests.get(url, headers=headers, verify=False)
                response.raise_for_status()
                project = response.json()
                projects = [project]
            else:
                # Get all projects
                url = f"{self.argocd_api_url}/api/v1/projects"
                response = requests.get(url, headers=headers, verify=False)
                response.raise_for_status()
                projects = response.json().get("items", [])
            
            result = {
                "project_count": len(projects),
                "projects": []
            }
            
            for proj in projects:
                proj_info = {
                    "name": proj.get("metadata", {}).get("name"),
                    "description": proj.get("spec", {}).get("description"),
                    "source_repos": proj.get("spec", {}).get("sourceRepos", []),
                    "destinations": proj.get("spec", {}).get("destinations", []),
                    "cluster_resource_whitelist": proj.get("spec", {}).get("clusterResourceWhitelist", []),
                    "namespace_resource_blacklist": proj.get("spec", {}).get("namespaceResourceBlacklist", [])
                }
                
                result["projects"].append(proj_info)
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting ArgoCD project information: {str(e)}")
            return {"error": str(e)}
    
    @tool("Sync an ArgoCD application")
    def sync_application(self, application_name: str, prune: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """
        Sync an ArgoCD application
        
        Args:
            application_name (str): Name of the application to sync
            prune (bool, optional): Whether to prune resources. Defaults to False.
            dry_run (bool, optional): Whether to perform a dry run. Defaults to False.
            
        Returns:
            dict: Sync operation result
        """
        headers = self._get_headers()
        headers["Content-Type"] = "application/json"
        
        try:
            url = f"{self.argocd_api_url}/api/v1/applications/{application_name}/sync"
            
            # Create sync options
            sync_options = []
            if prune:
                sync_options.append("Prune=true")
            
            data = {
                "dryRun": dry_run,
                "syncOptions": sync_options
            }
            
            response = requests.post(url, headers=headers, json=data, verify=False)
            response.raise_for_status()
            result = response.json()
            
            # Simplify the response
            return {
                "application": application_name,
                "revision": result.get("revision"),
                "operation_state": result.get("operationState", {}).get("phase"),
                "message": result.get("operationState", {}).get("message"),
                "dry_run": dry_run,
                "prune": prune
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error syncing ArgoCD application: {str(e)}")
            return {"error": str(e)}
    
    @tool("Get the sync status of an ArgoCD application")
    def get_application_sync_status(self, application_name: str) -> Dict[str, Any]:
        """
        Get the sync status of an ArgoCD application
        
        Args:
            application_name (str): Name of the application
            
        Returns:
            dict: Sync status information
        """
        # This is a simplified version of get_application focused on sync status
        headers = self._get_headers()
        
        try:
            url = f"{self.argocd_api_url}/api/v1/applications/{application_name}"
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            app = response.json()
            
            return {
                "application": application_name,
                "sync": {
                    "status": app.get("status", {}).get("sync", {}).get("status"),
                    "revision": app.get("status", {}).get("sync", {}).get("revision"),
                    "compared_to": app.get("status", {}).get("sync", {}).get("comparedTo", {})
                },
                "health": {
                    "status": app.get("status", {}).get("health", {}).get("status"),
                    "message": app.get("status", {}).get("health", {}).get("message")
                },
                "operation_state": app.get("status", {}).get("operationState", {}).get("phase"),
                "operation_message": app.get("status", {}).get("operationState", {}).get("message"),
                "resources_synced": bool(app.get("status", {}).get("sync", {}).get("status") == "Synced")
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting ArgoCD application sync status: {str(e)}")
            return {"error": str(e)}