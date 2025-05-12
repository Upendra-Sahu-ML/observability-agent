"""
ArgoCD tools for querying application deployment status
"""
import os
import logging
import requests
from common.tools.base import AgentTool

# Configure logging
logger = logging.getLogger(__name__)

class ArgoAppTool(AgentTool):
    """Tool for getting information about ArgoCD applications"""
    
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
    
    @property
    def name(self):
        return "argocd_app"
    
    @property
    def description(self):
        return "Get information about an ArgoCD application"
    
    def execute(self, application_name=None, application_namespace=None):
        """
        Get information about ArgoCD applications
        
        Args:
            application_name (str, optional): Name of the application
            application_namespace (str, optional): Namespace of the application
            
        Returns:
            dict: Information about the ArgoCD application
        """
        headers = {}
        if self.argocd_token:
            headers["Authorization"] = f"Bearer {self.argocd_token}"
        
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
    
    def get_application_resource_tree(self, application_name):
        """
        Get the resource tree for an ArgoCD application
        
        Args:
            application_name (str): Name of the application
            
        Returns:
            dict: Resource tree of the application
        """
        headers = {}
        if self.argocd_token:
            headers["Authorization"] = f"Bearer {self.argocd_token}"
        
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
    
    def get_application_events(self, application_name):
        """
        Get events for an ArgoCD application
        
        Args:
            application_name (str): Name of the application
            
        Returns:
            dict: Events for the application
        """
        headers = {}
        if self.argocd_token:
            headers["Authorization"] = f"Bearer {self.argocd_token}"
        
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
    

class ArgoProjectTool(AgentTool):
    """Tool for getting information about ArgoCD projects"""