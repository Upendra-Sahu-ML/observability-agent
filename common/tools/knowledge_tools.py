import os
import json
import logging
from typing import Dict, Any, List
from qdrant_client import QdrantClient
from qdrant_client.http import models
import markdown

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KnowledgeBaseTool:
    """Tool for managing the knowledge base"""
    
    def __init__(self):
        """Initialize the knowledge base tool"""
        # Initialize Qdrant client for vector storage
        self.qdrant_client = QdrantClient(
            url=os.environ.get("QDRANT_URL", "http://qdrant:6333")
        )
        
        # Ensure collections exist
        self._ensure_collections()
    
    def _ensure_collections(self):
        """Ensure required collections exist in Qdrant"""
        try:
            self.qdrant_client.get_collection("incidents")
        except Exception:
            self.qdrant_client.create_collection(
                collection_name="incidents",
                vectors_config=models.VectorParams(
                    size=1536,  # OpenAI embedding size
                    distance=models.Distance.COSINE
                )
            )
    
    def execute(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a knowledge base action
        
        Args:
            action (str): The action to perform (store, retrieve, search)
            data (Dict[str, Any]): The data for the action
            
        Returns:
            Dict[str, Any]: Result of the action
        """
        try:
            if action == "store":
                return self._store_incident(data)
            elif action == "retrieve":
                return self._retrieve_incident(data)
            elif action == "search":
                return self._search_incidents(data)
            else:
                return {"status": "error", "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Error executing knowledge base action: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def _store_incident(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store an incident in the knowledge base"""
        # Store in Qdrant with metadata
        self.qdrant_client.upsert(
            collection_name="incidents",
            points=[
                models.PointStruct(
                    id=data["alert_id"],
                    vector=data["embedding"],
                    payload={
                        "alert_id": data["alert_id"],
                        "title": data.get("title", ""),
                        "description": data.get("description", ""),
                        "root_cause": data.get("root_cause", ""),
                        "resolution": data.get("resolution", ""),
                        "timestamp": data.get("timestamp", ""),
                        "metadata": data.get("metadata", {})
                    }
                )
            ]
        )
        
        return {"status": "success", "message": "Incident stored successfully"}
    
    def _retrieve_incident(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve an incident from the knowledge base"""
        alert_id = data["alert_id"]
        
        try:
            result = self.qdrant_client.retrieve(
                collection_name="incidents",
                ids=[alert_id]
            )
            if result:
                return {"status": "success", "data": result[0].payload}
        except Exception as e:
            logger.error(f"Error retrieving incident: {str(e)}")
        
        return {"status": "error", "error": "Incident not found"}
    
    def _search_incidents(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Search for incidents in the knowledge base"""
        query = data["query"]
        limit = data.get("limit", 5)
        
        # Search in Qdrant
        results = self.qdrant_client.search(
            collection_name="incidents",
            query_vector=data["embedding"],
            limit=limit
        )
        
        return {
            "status": "success",
            "results": [hit.payload for hit in results]
        }

class PostmortemTemplateTool:
    """Tool for managing postmortem templates"""
    
    def __init__(self):
        """Initialize the postmortem template tool"""
        self.template_dir = os.environ.get("POSTMORTEM_TEMPLATE_DIR", "/app/templates")
    
    def execute(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a postmortem template action
        
        Args:
            action (str): The action to perform (get_template, fill_template)
            data (Dict[str, Any]): The data for the action
            
        Returns:
            Dict[str, Any]: Result of the action
        """
        try:
            if action == "get_template":
                return self._get_template(data)
            elif action == "fill_template":
                return self._fill_template(data)
            else:
                return {"status": "error", "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Error executing postmortem template action: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def _get_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get a postmortem template"""
        template_name = data.get("template_name", "default")
        template_path = os.path.join(self.template_dir, f"{template_name}.md")
        
        try:
            with open(template_path, "r") as f:
                template = f.read()
            return {"status": "success", "template": template}
        except FileNotFoundError:
            return {"status": "error", "error": f"Template not found: {template_name}"}
    
    def _fill_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Fill a postmortem template with incident data"""
        template = data["template"]
        incident_data = data["incident_data"]
        
        # Replace placeholders in template
        for key, value in incident_data.items():
            template = template.replace(f"{{{{ {key} }}}}", str(value))
        
        return {"status": "success", "filled_template": template}

class RunbookUpdateTool:
    """Tool for updating runbooks"""
    
    def __init__(self):
        """Initialize the runbook update tool"""
        self.runbook_dir = os.environ.get("RUNBOOK_DIR", "/app/runbooks")
    
    def execute(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a runbook update action
        
        Args:
            action (str): The action to perform (update, create)
            data (Dict[str, Any]): The data for the action
            
        Returns:
            Dict[str, Any]: Result of the action
        """
        try:
            if action == "update":
                return self._update_runbook(data)
            elif action == "create":
                return self._create_runbook(data)
            else:
                return {"status": "error", "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Error executing runbook update action: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def _update_runbook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing runbook"""
        runbook_name = data["runbook_name"]
        runbook_path = os.path.join(self.runbook_dir, f"{runbook_name}.md")
        
        try:
            with open(runbook_path, "r") as f:
                content = f.read()
            
            # Update content based on incident data
            updated_content = self._merge_runbook_content(content, data["incident_data"])
            
            with open(runbook_path, "w") as f:
                f.write(updated_content)
            
            return {"status": "success", "message": "Runbook updated successfully"}
        except FileNotFoundError:
            return {"status": "error", "error": f"Runbook not found: {runbook_name}"}
    
    def _create_runbook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new runbook"""
        runbook_name = data["runbook_name"]
        runbook_path = os.path.join(self.runbook_dir, f"{runbook_name}.md")
        
        try:
            content = self._generate_runbook_content(data["incident_data"])
            
            with open(runbook_path, "w") as f:
                f.write(content)
            
            return {"status": "success", "message": "Runbook created successfully"}
        except Exception as e:
            return {"status": "error", "error": f"Failed to create runbook: {str(e)}"}
    
    def _merge_runbook_content(self, existing_content: str, incident_data: Dict[str, Any]) -> str:
        """Merge incident data into existing runbook content"""
        # Convert existing content to HTML for easier manipulation
        html_content = markdown.markdown(existing_content)
        
        # Add new incident data
        new_section = f"""
## Recent Incident: {incident_data['title']}

**Date:** {incident_data['timestamp']}
**Root Cause:** {incident_data['root_cause']}
**Resolution:** {incident_data['resolution']}

### Lessons Learned
{incident_data.get('lessons_learned', 'No specific lessons documented.')}
"""
        
        # Convert back to markdown
        return existing_content + new_section
    
    def _generate_runbook_content(self, incident_data: Dict[str, Any]) -> str:
        """Generate new runbook content from incident data"""
        return f"""# {incident_data['title']}

## Overview
{incident_data.get('description', 'No description provided.')}

## Root Cause
{incident_data['root_cause']}

## Resolution Steps
{incident_data['resolution']}

## Lessons Learned
{incident_data.get('lessons_learned', 'No specific lessons documented.')}

## Related Incidents
- {incident_data['alert_id']} ({incident_data['timestamp']})
""" 