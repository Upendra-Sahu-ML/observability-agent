import os
import re
import logging
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import markdown
import base64
from urllib.parse import urlparse
from crewai.tools import tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RunbookSourceBase:
    """Base class for runbook sources"""
    def fetch_runbook(self, identifier):
        """Fetches a runbook from the source"""
        raise NotImplementedError("Subclasses must implement this method")

    def _parse_steps(self, content):
        """Parse the content to extract steps"""
        raise NotImplementedError("Subclasses must implement this method")

class GitHubMarkdownRunbookSource(RunbookSourceBase):
    """Fetches runbooks from GitHub Markdown files"""

    def __init__(self, token=None, repo=None, branch="main", path="runbooks"):
        """
        Initialize the GitHub Markdown Runbook Source

        Args:
            token (str): GitHub personal access token
            repo (str): Repository in format 'owner/repo'
            branch (str): Branch name, defaults to 'main'
            path (str): Path to runbooks directory in the repo
        """
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.repo = repo or os.environ.get("RUNBOOK_GITHUB_REPO")
        self.branch = branch or os.environ.get("RUNBOOK_GITHUB_BRANCH", "main")
        self.path = path or os.environ.get("RUNBOOK_GITHUB_PATH", "runbooks")

        if not self.repo:
            logger.warning("No GitHub repository specified, GitHub runbook source will be unavailable")

        self.headers = {}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def fetch_runbook(self, identifier):
        """
        Fetch a runbook from GitHub

        Args:
            identifier (dict): Dictionary containing alert information

        Returns:
            dict: Runbook data with steps
        """
        if not self.repo:
            logger.warning("GitHub repository not configured")
            return {"found": False, "message": "GitHub repository not configured"}

        # Extract alert name and service
        alert_name = identifier.get('labels', {}).get('alertname', '')
        service = identifier.get('labels', {}).get('service', '')

        if not alert_name:
            return {"found": False, "message": "No alert name provided"}

        # Define possible file paths to check
        possible_paths = []

        # Try with service-specific runbook first
        if service:
            possible_paths.append(f"{self.path}/{service}/{alert_name}.md")
            possible_paths.append(f"{self.path}/{service}-{alert_name}.md")

        # Then try with just alert name
        possible_paths.append(f"{self.path}/{alert_name}.md")

        # Try a generic runbooks file
        possible_paths.append(f"{self.path}/runbooks.md")

        for path in possible_paths:
            try:
                # GitHub API URL to fetch file content
                url = f"https://api.github.com/repos/{self.repo}/contents/{path}?ref={self.branch}"

                response = requests.get(url, headers=self.headers, timeout=10)

                if response.status_code == 200:
                    content_data = response.json()
                    if content_data.get("type") == "file":
                        # GitHub API returns content as base64 encoded
                        content = base64.b64decode(content_data["content"]).decode("utf-8")

                        # Parse steps from the markdown content
                        steps = self._parse_steps(content)

                        return {
                            "alertName": alert_name,
                            "service": service,
                            "steps": steps,
                            "found": True,
                            "source": f"GitHub: {self.repo}/{path}"
                        }
            except Exception as e:
                logger.error(f"Error fetching runbook from GitHub {path}: {str(e)}")
                continue

        # If we get here, no runbook was found
        return {
            "alertName": alert_name,
            "service": service,
            "steps": [],
            "found": False,
            "message": f"No runbook found for alert {alert_name}"
        }

    def _parse_steps(self, content):
        """
        Parse markdown content to extract steps

        Args:
            content (str): Markdown content

        Returns:
            list: List of steps extracted from the markdown
        """
        steps = []

        # Look for H2 or H3 sections titled "Steps", "Remediation", "Resolution", etc.
        sections = re.split(r'#{2,3}\s+(Steps|Remediation Steps|Resolution Steps|How to Fix|Runbook|Resolution|Remediation)', content, flags=re.IGNORECASE)

        if len(sections) > 1:
            # Take the content after the heading
            steps_section = sections[2]  # Format is [before, heading, content, heading, content, ...]

            # Split by numbered list items or bullet points
            raw_steps = re.findall(r'(?:^\d+\.|\*)\s+(.+?)(?=^\d+\.|\*|$)', steps_section, re.MULTILINE | re.DOTALL)

            if raw_steps:
                steps = [step.strip() for step in raw_steps]
            else:
                # If no numbered list found, split by newlines and treat paragraphs as steps
                step_candidates = [s.strip() for s in steps_section.split('\n\n') if s.strip()]
                steps = [s for s in step_candidates if len(s) > 10]  # Eliminate very short lines
        else:
            # Look for any numbered list in the document
            raw_steps = re.findall(r'(?:^\d+\.|\*)\s+(.+?)(?=^\d+\.|\*|$)', content, re.MULTILINE | re.DOTALL)
            if raw_steps:
                steps = [step.strip() for step in raw_steps]

        return steps

class GitHubPagesRunbookSource(RunbookSourceBase):
    """Fetches runbooks from GitHub Pages or any HTML page"""

    def __init__(self, base_url=None):
        """
        Initialize the GitHub Pages Runbook Source

        Args:
            base_url (str): Base URL for the GitHub Pages site
        """
        self.base_url = base_url or os.environ.get("RUNBOOK_HTML_BASE_URL")

        if not self.base_url:
            logger.warning("No HTML base URL specified, HTML runbook source will be unavailable")

    def fetch_runbook(self, identifier):
        """
        Fetch a runbook from GitHub Pages or HTML site

        Args:
            identifier (dict): Dictionary containing alert information

        Returns:
            dict: Runbook data with steps
        """
        if not self.base_url:
            logger.warning("HTML base URL not configured")
            return {"found": False, "message": "HTML base URL not configured"}

        # Extract alert name and service
        alert_name = identifier.get('labels', {}).get('alertname', '')
        service = identifier.get('labels', {}).get('service', '')

        if not alert_name:
            return {"found": False, "message": "No alert name provided"}

        # Define possible URLs to check
        possible_urls = []

        # Check if base_url ends with a slash
        base_url = self.base_url
        if not base_url.endswith('/'):
            base_url += '/'

        # Try with service-specific runbook first
        if service:
            possible_urls.append(f"{base_url}{service}/{alert_name}.html")
            possible_urls.append(f"{base_url}runbooks/{service}/{alert_name}.html")
            possible_urls.append(f"{base_url}runbooks/{service}-{alert_name}.html")

        # Then try with just alert name
        possible_urls.append(f"{base_url}{alert_name}.html")
        possible_urls.append(f"{base_url}runbooks/{alert_name}.html")

        # Try a generic runbooks page
        possible_urls.append(f"{base_url}runbooks.html")

        for url in possible_urls:
            try:
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    # Parse HTML content
                    content = response.text
                    steps = self._parse_steps(content)

                    if steps:
                        return {
                            "alertName": alert_name,
                            "service": service,
                            "steps": steps,
                            "found": True,
                            "source": f"HTML: {url}"
                        }
            except Exception as e:
                logger.error(f"Error fetching runbook from HTML {url}: {str(e)}")
                continue

        # If we get here, no runbook was found
        return {
            "alertName": alert_name,
            "service": service,
            "steps": [],
            "found": False,
            "message": f"No runbook found for alert {alert_name}"
        }

    def _parse_steps(self, content):
        """
        Parse HTML content to extract steps

        Args:
            content (str): HTML content

        Returns:
            list: List of steps extracted from the HTML
        """
        steps = []

        try:
            soup = BeautifulSoup(content, 'html.parser')

            # First try to find a specific section for remediation steps
            remediation_section = None

            # Look for headings with relevant text
            for heading in soup.find_all(['h1', 'h2', 'h3']):
                if re.search(r'(Steps|Remediation|Resolution|How to Fix|Runbook)', heading.text, re.IGNORECASE):
                    remediation_section = heading
                    break

            # If we found a remediation section, extract steps from there
            if remediation_section:
                # Get the next elements after the heading until the next heading
                current = remediation_section.next_sibling

                # Look for ordered or unordered lists
                while current and not (hasattr(current, 'name') and current.name in ['h1', 'h2', 'h3']):
                    if hasattr(current, 'name') and current.name in ['ol', 'ul']:
                        for li in current.find_all('li'):
                            step_text = li.get_text(strip=True)
                            if step_text:
                                steps.append(step_text)
                        break
                    current = current.next_sibling

                # If no list found but there are paragraphs, treat them as steps
                if not steps:
                    current = remediation_section.next_sibling
                    while current and not (hasattr(current, 'name') and current.name in ['h1', 'h2', 'h3']):
                        if hasattr(current, 'name') and current.name == 'p':
                            step_text = current.get_text(strip=True)
                            if step_text and len(step_text) > 10:  # Ignore very short paragraphs
                                steps.append(step_text)
                        current = current.next_sibling

            # If we couldn't find steps from a specific section, look for any ordered list
            if not steps:
                for ol in soup.find_all('ol'):
                    for li in ol.find_all('li'):
                        step_text = li.get_text(strip=True)
                        if step_text:
                            steps.append(step_text)
                    if steps:  # Take the first ordered list with content
                        break

            # If still no steps, try unordered lists
            if not steps:
                for ul in soup.find_all('ul'):
                    for li in ul.find_all('li'):
                        step_text = li.get_text(strip=True)
                        if step_text:
                            steps.append(step_text)
                    if steps:  # Take the first unordered list with content
                        break

        except Exception as e:
            logger.error(f"Error parsing HTML content: {str(e)}")

        return steps

class LocalFileRunbookSource(RunbookSourceBase):
    """Fetches runbooks from local files"""

    def __init__(self, base_path=None):
        """
        Initialize the Local File Runbook Source

        Args:
            base_path (str): Base path for local runbook files
        """
        self.base_path = base_path or os.environ.get("RUNBOOK_LOCAL_PATH", "/runbooks")

    def fetch_runbook(self, identifier):
        """
        Fetch a runbook from local files

        Args:
            identifier (dict): Dictionary containing alert information

        Returns:
            dict: Runbook data with steps
        """
        # Extract alert name and service
        alert_name = identifier.get('labels', {}).get('alertname', '')
        service = identifier.get('labels', {}).get('service', '')

        if not alert_name:
            return {"found": False, "message": "No alert name provided"}

        # Define possible file paths to check
        possible_paths = []

        # Try with service-specific runbook first
        if service:
            possible_paths.append(os.path.join(self.base_path, service, f"{alert_name}.md"))
            possible_paths.append(os.path.join(self.base_path, f"{service}-{alert_name}.md"))

        # Then try with just alert name
        possible_paths.append(os.path.join(self.base_path, f"{alert_name}.md"))

        # Try a generic runbooks file
        possible_paths.append(os.path.join(self.base_path, "runbooks.md"))

        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        content = f.read()

                    # Parse steps from the markdown content
                    steps = self._parse_steps(content)

                    return {
                        "alertName": alert_name,
                        "service": service,
                        "steps": steps,
                        "found": True,
                        "source": f"Local file: {path}"
                    }
                except Exception as e:
                    logger.error(f"Error reading local runbook file {path}: {str(e)}")
                    continue

        # If we get here, no runbook was found
        return {
            "alertName": alert_name,
            "service": service,
            "steps": [],
            "found": False,
            "message": f"No runbook found for alert {alert_name}"
        }

    def _parse_steps(self, content):
        """
        Parse markdown content to extract steps - reuse the same parser as GitHubMarkdownRunbookSource
        """
        # Create a temporary GitHubMarkdownRunbookSource just to use its parsing method
        github_source = GitHubMarkdownRunbookSource()
        return github_source._parse_steps(content)

class RunbookFetchTool:
    """Tool to fetch runbooks from multiple sources"""

    def __init__(self):
        """Initialize the runbook fetch tool with multiple sources"""
        # Initialize sources in priority order
        self.sources = []

        # Add local file source
        self.sources.append(LocalFileRunbookSource())

        # Add GitHub markdown source if configured
        github_repo = os.environ.get("RUNBOOK_GITHUB_REPO")
        if github_repo:
            self.sources.append(GitHubMarkdownRunbookSource())

        # Add HTML source if configured
        html_base_url = os.environ.get("RUNBOOK_HTML_BASE_URL")
        if html_base_url:
            self.sources.append(GitHubPagesRunbookSource())

        logger.info(f"Initialized runbook fetch tool with {len(self.sources)} sources")

    def fetch(self, alert_data):
        """
        Fetch a runbook from all configured sources

        Args:
            alert_data (dict): Alert data containing labels and annotations

        Returns:
            dict: Runbook data with steps from the first source that finds a runbook
        """
        # Try each source in order until we find a runbook
        for source in self.sources:
            try:
                result = source.fetch_runbook(alert_data)
                if result.get("found", False):
                    return result
            except Exception as e:
                logger.error(f"Error fetching runbook from source {source.__class__.__name__}: {str(e)}")
                continue

        # If no source found a runbook, return a generic error
        return {
            "alertName": alert_data.get('labels', {}).get('alertname', 'unknown'),
            "service": alert_data.get('labels', {}).get('service', ''),
            "steps": [],
            "found": False,
            "message": "No runbook found in any configured source"
        }

class RunbookSearchTool:
    """Tool for searching for runbooks based on incident details"""

    def __init__(self, runbook_dir=None, additional_sources=None):
        """
        Initialize the runbook search tool

        Args:
            runbook_dir (str, optional): Directory containing runbook files
            additional_sources (list, optional): Additional runbook sources to use
        """
        self.runbook_dir = runbook_dir or os.environ.get("RUNBOOK_LOCAL_PATH", "/runbooks")
        self.fetch_tool = RunbookFetchTool()

        # Add additional sources if provided
        self.additional_sources = additional_sources or []

    @tool("Search for relevant runbooks based on incident details")
    def search_runbooks(self, incident_type: str, service: str = None, keywords: list = None, max_results: int = 3):
        """
        Search for relevant runbooks based on incident details

        Args:
            incident_type (str): Type of incident to search runbooks for
            service (str, optional): Service related to the incident
            keywords (list, optional): List of keywords to search for
            max_results (int, optional): Maximum number of runbooks to return

        Returns:
            dict: Search results containing matching runbooks
        """
        # Create a mock alert data structure to use with fetch_tool
        alert_data = {
            'labels': {
                'alertname': incident_type,
                'service': service or ''
            },
            'annotations': {
                'keywords': ','.join(keywords) if keywords else ''
            }
        }

        # Fetch the runbook using the fetch tool
        result = self.fetch_tool.fetch(alert_data)

        # If fetch_tool found a runbook, return it as the first result
        if result.get("found", False):
            return {
                "status": "success",
                "runbooks": [result],
                "count": 1
            }

        # If no runbook was found, try additional sources if available
        if self.additional_sources:
            for source in self.additional_sources:
                try:
                    # Use asyncio.run to run the async fetch_runbook method
                    import asyncio
                    source_result = asyncio.run(source.fetch_runbook(alert_data))
                    if source_result.get("found", False):
                        return {
                            "status": "success",
                            "runbooks": [source_result],
                            "count": 1
                        }
                except Exception as e:
                    logger.error(f"Error fetching runbook from additional source: {str(e)}")

        # If still no runbook was found, return an empty result
        return {
            "status": "error",
            "message": f"No runbooks found for incident type: {incident_type}, service: {service}",
            "runbooks": [],
            "count": 0
        }

    @tool("Get runbook for a specific service and alert")
    def get_runbook_by_alert(self, alert_name: str, service: str = None):
        """
        Get a specific runbook for a service and alert name

        Args:
            alert_name (str): Name of the alert
            service (str, optional): Service name

        Returns:
            dict: Runbook data if found
        """
        alert_data = {
            'labels': {
                'alertname': alert_name,
                'service': service or ''
            }
        }

        # First try the standard fetch tool
        result = self.fetch_tool.fetch(alert_data)

        # If a runbook was found, return it
        if result.get("found", False):
            return result

        # If no runbook was found, try additional sources if available
        if self.additional_sources:
            for source in self.additional_sources:
                try:
                    # Use asyncio.run to run the async fetch_runbook method
                    import asyncio
                    source_result = asyncio.run(source.fetch_runbook(alert_data))
                    if source_result.get("found", False):
                        return source_result
                except Exception as e:
                    logger.error(f"Error fetching runbook from additional source: {str(e)}")

        # If still no runbook was found, return the original result
        return result

class RunbookExecutionTool:
    """Tool for executing runbook steps and tracking progress"""

    def __init__(self, js=None):
        """Initialize the runbook execution tool with JetStream client"""
        self.js = js
        self.executions = {}  # In-memory store of executions

    def set_jetstream(self, js):
        """Set the JetStream client"""
        self.js = js

    @tool("Execute runbook steps and track progress")
    def execute_runbook(self, runbook_id: str = None, incident_id: str = None, steps: list = None, execution_id: str = None):
        """
        Execute runbook steps and track progress

        Args:
            runbook_id (str): ID of the runbook to execute
            incident_id (str): ID of the incident being addressed
            steps (list, optional): List of steps to execute if not using a standard runbook
            execution_id (str, optional): ID of the execution to track

        Returns:
            dict: Execution results with step status and outcomes
        """
        # Generate execution ID if not provided
        if not execution_id:
            execution_id = f"exec-{datetime.now().strftime('%Y%m%d%H%M%S')}-{runbook_id}"

        # If no steps provided, use empty list
        if not steps:
            steps = ["No steps provided"]

        # Create execution record
        execution = {
            "execution_id": execution_id,
            "runbook_id": runbook_id or "custom",
            "incident_id": incident_id,
            "status": "in_progress",
            "progress": 0,
            "start_time": datetime.now().isoformat(),
            "steps": [{"step_number": i+1, "description": step, "status": "pending"} for i, step in enumerate(steps)],
            "current_step": 0,
            "steps_total": len(steps)
        }

        # Store execution in memory
        self.executions[execution_id] = execution

        # Start execution in background thread
        import threading
        thread = threading.Thread(target=self._execute_steps, args=(execution_id,))
        thread.daemon = True
        thread.start()

        # Return initial status
        return {
            "execution_id": execution_id,
            "runbook_id": runbook_id or "custom",
            "incident_id": incident_id,
            "status": "in_progress",
            "progress": 0,
            "steps_total": len(steps)
        }

    def _execute_steps(self, execution_id):
        """
        Execute runbook steps in background

        Args:
            execution_id (str): ID of the execution to process
        """
        import time

        execution = self.executions.get(execution_id)
        if not execution:
            logger.error(f"Execution {execution_id} not found")
            return

        steps = execution["steps"]
        total_steps = len(steps)

        # Process each step
        for i, step in enumerate(steps):
            # Update current step
            execution["current_step"] = i
            step["status"] = "in_progress"
            self._publish_status_update(execution)

            # Log step execution
            logger.info(f"Executing step {i+1}/{total_steps} for execution {execution_id}: {step['description']}")

            # Simulate step execution (in real implementation, would actually execute commands)
            try:
                # Simulate execution time
                time.sleep(5)  # 5 seconds per step

                # Execute the step (this would be real execution in production)
                result = self._execute_single_step(step["description"])

                # Update step status
                step["status"] = "completed"
                step["outcome"] = result

                # Update progress
                execution["progress"] = int(((i + 1) / total_steps) * 100)

                # Publish status update
                self._publish_status_update(execution)

            except Exception as e:
                logger.error(f"Error executing step {i+1}: {str(e)}")
                step["status"] = "failed"
                step["outcome"] = f"Error: {str(e)}"
                execution["status"] = "failed"
                self._publish_status_update(execution)
                return

        # All steps completed
        execution["status"] = "completed"
        execution["end_time"] = datetime.now().isoformat()
        execution["progress"] = 100

        # Publish final status update
        self._publish_status_update(execution)
        logger.info(f"Execution {execution_id} completed successfully")

    def _execute_single_step(self, step_description):
        """
        Execute a single runbook step

        Args:
            step_description (str): Description of the step to execute

        Returns:
            str: Result of the step execution
        """
        # In a real implementation, this would parse the step and execute appropriate commands
        # For now, we'll just return a simulated result
        return f"Step executed successfully: {step_description}"

    def _publish_status_update(self, execution):
        """
        Publish execution status update to NATS

        Args:
            execution (dict): Execution record to publish
        """
        if not self.js:
            logger.warning("JetStream not available, skipping status update")
            return

        try:
            # Create a copy of the execution with only the necessary fields
            status_update = {
                "execution_id": execution["execution_id"],
                "runbook_id": execution["runbook_id"],
                "status": execution["status"],
                "progress": execution["progress"],
                "current_step": execution["current_step"],
                "steps": execution["steps"],
                "timestamp": datetime.now().isoformat()
            }

            # Publish to runbook.status.<execution_id>
            import json
            import asyncio

            async def publish():
                try:
                    await self.js.publish(
                        f"runbook.status.{execution['execution_id']}",
                        json.dumps(status_update).encode()
                    )
                    logger.info(f"Published status update for execution {execution['execution_id']}")
                except Exception as e:
                    logger.error(f"Error publishing status update: {str(e)}")

            # Run the async publish function
            asyncio.run(publish())

        except Exception as e:
            logger.error(f"Error publishing status update: {str(e)}")

    @tool("Track runbook execution status")
    def track_execution(self, execution_id: str):
        """
        Track the status of a runbook execution

        Args:
            execution_id (str): ID of the execution to track

        Returns:
            dict: Current status of the runbook execution
        """
        # Check if execution exists in memory
        execution = self.executions.get(execution_id)
        if execution:
            return {
                "execution_id": execution["execution_id"],
                "runbook_id": execution["runbook_id"],
                "status": execution["status"],
                "progress": execution["progress"],
                "steps_completed": sum(1 for step in execution["steps"] if step["status"] == "completed"),
                "steps_total": len(execution["steps"]),
                "current_step": execution["current_step"],
                "steps": execution["steps"],
                "last_updated": datetime.now().isoformat()
            }

        # If not in memory, return a default response
        return {
            "execution_id": execution_id,
            "status": "unknown",
            "message": "Execution not found or completed"
        }

    @tool("Generate custom runbook")
    def generate_custom_runbook(self, incident_type: str, service: str, root_cause: str):
        """
        Generate a custom runbook based on incident details and root cause

        Args:
            incident_type (str): Type of incident
            service (str): Name of the affected service
            root_cause (str): Description of the root cause

        Returns:
            dict: Custom runbook data
        """
        # In a real implementation, this might use a template system or an LLM to generate steps
        # For now, return a simple example
        return {
            "alertName": incident_type,
            "service": service,
            "steps": [
                f"1. Verify the {service} service is experiencing issues related to {incident_type}",
                f"2. Check the root cause: {root_cause}",
                f"3. Restart the {service} service if necessary",
                "4. Verify the service is operating correctly",
                "5. Document the incident resolution"
            ],
            "found": True,
            "source": "Generated custom runbook"
        }