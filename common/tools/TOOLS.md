# Observability Agent System Tools Documentation

This documentation describes the tools available in the `common/tools` directory and their integration with the Observability Agent System.

## Directory Structure
```
common/tools/
├── TOOLS.md                 # This documentation
├── knowledge_tools.py       # Knowledge base and incident management tools
├── notification_tools.py    # Multi-channel notification tools
└── templates/              # Template directory for postmortems and runbooks
```

## Core Tools Overview

### 1. Knowledge Tools (`knowledge_tools.py`)

#### Purpose
The Knowledge Tools provide a centralized system for storing, retrieving, and analyzing incident data using vector storage (Qdrant). They enable intelligent incident management and pattern recognition.

#### Components

1. **KnowledgeBaseTool**
   - **Purpose**: Manages incident data storage and retrieval
   - **Key Features**:
     - Vector storage for semantic search
     - Metadata management
     - Historical incident tracking
   - **Use Cases**:
     - Storing incident details
     - Finding similar past incidents
     - Pattern recognition across incidents
   - **Example**:
     ```python
     from common.tools.knowledge_tools import KnowledgeBaseTool
     
     # Initialize tool
     knowledge_tool = KnowledgeBaseTool()
     
     # Store an incident
     knowledge_tool.store_incident(incident_data)
     
     # Search similar incidents
     similar_incidents = knowledge_tool.search_similar(incident_vector)
     ```

2. **PostmortemTemplateTool**
   - **Purpose**: Manages postmortem documentation templates
   - **Key Features**:
     - Template management
     - Dynamic content generation
     - Version control
   - **Use Cases**:
     - Creating standardized postmortems
     - Maintaining documentation consistency
     - Tracking incident resolutions
   - **Example**:
     ```python
     from common.tools.knowledge_tools import PostmortemTemplateTool
     
     # Initialize tool
     template_tool = PostmortemTemplateTool()
     
     # Generate postmortem
     postmortem = template_tool.generate_postmortem(incident_data)
     ```

3. **RunbookUpdateTool**
   - **Purpose**: Manages runbook updates based on incident learnings
   - **Key Features**:
     - Runbook versioning
     - Update tracking
     - Change history
   - **Use Cases**:
     - Updating runbooks after incidents
     - Maintaining operational documentation
     - Tracking procedural changes
   - **Example**:
     ```python
     from common.tools.knowledge_tools import RunbookUpdateTool
     
     # Initialize tool
     runbook_tool = RunbookUpdateTool()
     
     # Update runbook
     runbook_tool.update_runbook(incident_id, new_procedures)
     ```

### 2. Notification Tools (`notification_tools.py`)

#### Purpose
The Notification Tools provide a unified interface for sending alerts and notifications across multiple channels, ensuring timely communication of incidents.

#### Components

1. **SlackNotificationTool**
   - **Purpose**: Manages Slack notifications
   - **Key Features**:
     - Channel management
     - Message formatting
     - Thread support
   - **Use Cases**:
     - Team notifications
     - Incident updates
     - Status reports
   - **Example**:
     ```python
     from common.tools.notification_tools import SlackNotificationTool
     
     # Initialize tool
     slack_tool = SlackNotificationTool()
     
     # Send Slack notification
     slack_tool.send_alert(channel, message, severity)
     ```

2. **PagerDutyNotificationTool**
   - **Purpose**: Manages PagerDuty incident creation and updates
   - **Key Features**:
     - Incident management
     - Priority handling
     - On-call routing
   - **Use Cases**:
     - Critical incident alerts
     - On-call notifications
     - Incident escalation
   - **Example**:
     ```python
     from common.tools.notification_tools import PagerDutyNotificationTool
     
     # Initialize tool
     pagerduty_tool = PagerDutyNotificationTool()
     
     # Create PagerDuty incident
     pagerduty_tool.create_incident(service, description, priority)
     ```

3. **WebexNotificationTool**
   - **Purpose**: Manages Webex notifications
   - **Key Features**:
     - Space management
     - Message formatting
     - File sharing
   - **Use Cases**:
     - Team communications
     - Status updates
     - File sharing
   - **Example**:
     ```python
     from common.tools.notification_tools import WebexNotificationTool
     
     # Initialize tool
     webex_tool = WebexNotificationTool()
     
     # Send Webex message
     webex_tool.send_message(space_id, message, attachments)
     ```

## Tool Integration

### 1. Knowledge Base Integration
- **Purpose**: Provides intelligent incident management
- **Benefits**:
  - Historical pattern recognition
  - Similar incident detection
  - Automated documentation
- **Integration Points**:
  - Incident storage
  - Pattern analysis
  - Documentation generation

### 2. Notification System Integration
- **Purpose**: Ensures timely incident communication
- **Benefits**:
  - Multi-channel alerts
  - Priority-based routing
  - Consistent messaging
- **Integration Points**:
  - Alert distribution
  - Status updates
  - Team notifications

## Best Practices

### 1. Knowledge Tools
- Regular vector database maintenance
- Template version control
- Runbook update tracking
- Incident data validation

### 2. Notification Tools
- Rate limiting implementation
- Message templating
- Channel prioritization
- Delivery tracking

## Configuration

### 1. Knowledge Base
```yaml
knowledge_base:
  qdrant_url: "http://localhost:6333"
  collection_name: "incidents"
  vector_size: 768
  template_dir: "/templates"
  runbook_dir: "/runbooks"
```

### 2. Notification System
```yaml
notifications:
  slack:
    webhook_url: "https://hooks.slack.com/services/..."
    default_channel: "#alerts"
  pagerduty:
    api_key: "your-api-key"
    service_id: "your-service-id"
  webex:
    access_token: "your-access-token"
    default_space: "your-space-id"
```

## Troubleshooting

### 1. Knowledge Base Issues
- Vector database connectivity
- Collection management
- Template loading
- Runbook updates

### 2. Notification Issues
- Channel connectivity
- Message delivery
- Rate limiting
- Authentication

## Future Enhancements

### 1. Knowledge Tools
- Advanced pattern recognition
- Machine learning integration
- Automated categorization
- Enhanced search capabilities

### 2. Notification Tools
- Additional channels
- Advanced templating
- Delivery analytics
- Custom workflows 