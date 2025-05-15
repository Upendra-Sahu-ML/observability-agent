import os
import json
import logging
from typing import Dict, Any, List
from qdrant_client import QdrantClient
from qdrant_client.http import models
import markdown
from datetime import datetime
from crewai.tools import tool

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
    
    @tool("Store incident data in the knowledge base")
    def store_incident(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store an incident in the knowledge base
        
        Args:
            data (dict): Incident data including alert_id, embedding, title, description, etc.
            
        Returns:
            dict: Status of the store operation
        """
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
    
    @tool("Retrieve incident data from the knowledge base by ID")
    def retrieve_incident(self, alert_id: str) -> Dict[str, Any]:
        """
        Retrieve an incident from the knowledge base
        
        Args:
            alert_id (str): ID of the alert/incident to retrieve
            
        Returns:
            dict: Incident data if found, error status otherwise
        """
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
    
    @tool("Search for similar incidents in the knowledge base")
    def search_incidents(self, query: str, embedding: list, limit: int = 5) -> Dict[str, Any]:
        """
        Search for incidents in the knowledge base
        
        Args:
            query (str): Text query to search for
            embedding (list): Vector embedding of the query
            limit (int, optional): Maximum number of results to return
            
        Returns:
            dict: Search results with matching incidents
        """
        # Search in Qdrant
        results = self.qdrant_client.search(
            collection_name="incidents",
            query_vector=embedding,
            limit=limit
        )
        
        return {
            "status": "success",
            "results": [hit.payload for hit in results]
        }

class PostmortemTemplateTool:
    """Tool for managing postmortem templates"""
    
    def __init__(self, template_dir=None):
        """Initialize the postmortem template tool"""
        self.template_dir = template_dir or os.environ.get("POSTMORTEM_TEMPLATE_DIR", "/app/templates")
    
    @tool("Get a postmortem template by name")
    def get_template(self, template_name: str = "default") -> Dict[str, Any]:
        """
        Get a postmortem template
        
        Args:
            template_name (str, optional): Name of the template to retrieve
            
        Returns:
            dict: Template content if found, error status otherwise
        """
        template_path = os.path.join(self.template_dir, f"{template_name}.md")
        
        try:
            with open(template_path, "r") as f:
                template = f.read()
            return {"status": "success", "template": template}
        except FileNotFoundError:
            return {"status": "error", "error": f"Template not found: {template_name}"}
    
    @tool("Fill a template with incident data")
    def fill_template(self, template: str, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fill a postmortem template with incident data
        
        Args:
            template (str): Template content with placeholders
            incident_data (dict): Data to fill in the template
            
        Returns:
            dict: Filled template content
        """
        # Replace placeholders in template
        for key, value in incident_data.items():
            template = template.replace(f"{{{{ {key} }}}}", str(value))
        
        return {"status": "success", "filled_template": template}

class RunbookUpdateTool:
    """Tool for updating runbooks"""
    
    def __init__(self):
        """Initialize the runbook update tool"""
        self.runbook_dir = os.environ.get("RUNBOOK_DIR", "/app/runbooks")
    
    @tool("Update an existing runbook with new information")
    def update_runbook(self, runbook_name: str, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing runbook
        
        Args:
            runbook_name (str): Name of the runbook to update
            incident_data (dict): New incident data to add to the runbook
            
        Returns:
            dict: Status of the update operation
        """
        runbook_path = os.path.join(self.runbook_dir, f"{runbook_name}.md")
        
        try:
            with open(runbook_path, "r") as f:
                content = f.read()
            
            # Update content based on incident data
            updated_content = self._merge_runbook_content(content, incident_data)
            
            with open(runbook_path, "w") as f:
                f.write(updated_content)
            
            return {"status": "success", "message": "Runbook updated successfully"}
        except FileNotFoundError:
            return {"status": "error", "error": f"Runbook not found: {runbook_name}"}
    
    @tool("Create a new runbook from incident data")
    def create_runbook(self, runbook_name: str, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new runbook
        
        Args:
            runbook_name (str): Name for the new runbook
            incident_data (dict): Incident data to use in the runbook
            
        Returns:
            dict: Status of the create operation
        """
        runbook_path = os.path.join(self.runbook_dir, f"{runbook_name}.md")
        
        try:
            content = self._generate_runbook_content(incident_data)
            
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

class PostmortemGeneratorTool:
    """Tool for generating comprehensive postmortem documents"""
    
    @tool("Generate a comprehensive postmortem document")
    def generate_postmortem(self, incident_data: Dict[str, Any], 
                root_cause: str = "", 
                impact: str = "", 
                resolution: str = "", 
                **kwargs) -> Dict[str, Any]:
        """
        Generate a comprehensive postmortem document
        
        Args:
            incident_data (dict): Data about the incident
            root_cause (str): Identified root cause of the incident
            impact (str): Description of the impact of the incident
            resolution (str): How the incident was resolved
            
        Returns:
            dict: Generated postmortem document
        """
        try:
            # Extract incident details
            alert_id = incident_data.get("alert_id", "unknown")
            service = incident_data.get("service", "unknown")
            severity = incident_data.get("severity", "unknown")
            description = incident_data.get("description", "No description provided")
            timestamp = incident_data.get("timestamp", "unknown")
            
            # Build the document
            postmortem = f"""# Incident Postmortem: {service} {severity.upper()} Incident {alert_id}

## Executive Summary
{description}

## Incident Timeline
- **Detection**: {timestamp}
- **Acknowledgment**: Shortly after detection
- **Resolution**: Detailed in resolution steps below

## Root Cause Analysis
{root_cause}

## Impact Assessment
{impact if impact else "Impact assessment not provided."}

## Mitigation Steps
{resolution if resolution else "Resolution steps not provided."}

## Prevention Measures
Based on the root cause analysis, here are recommended prevention measures:
- Implement monitoring for this specific failure mode
- Add alerting for early detection of similar issues
- Consider adding redundancy or fallback mechanisms

## Lessons Learned
- Importance of quick incident detection and response
- Value of comprehensive monitoring
- Need for clear communication during incidents

## Action Items
1. Review monitoring for the affected system
2. Update runbooks with new information from this incident
3. Schedule a follow-up review in 2 weeks to check prevention measures
4. Conduct a training session on the lessons learned
"""
            
            return {
                "status": "success", 
                "postmortem": postmortem,
                "format": "markdown"
            }
            
        except Exception as e:
            logger.error(f"Error generating postmortem: {str(e)}")
            return {
                "status": "error", 
                "error": str(e)
            }