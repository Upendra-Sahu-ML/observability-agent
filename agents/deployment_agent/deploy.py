import redis
import json
import os
from crewai import Agent, Task, Crew
from crewai.tasks import TaskOutput
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from common.tools.deployment_tools import (
    GitChangeTool,
    ArgoCDTool,
    KubeDeploymentTool
)

load_dotenv()

class DeploymentAgent:
    def __init__(self, argocd_server="https://argocd-server.argocd:443", git_repo_path="/app/repo"):
        self.redis_client = redis.Redis(host='redis', port=6379)
        self.git_repo_path = git_repo_path
        
        # Initialize OpenAI model
        self.llm = ChatOpenAI(model="gpt-4")
        
        # Initialize Deployment tools
        self.git_tool = GitChangeTool()
        
        # ArgoCD tool requires API token from environment or explicit config
        try:
            self.argocd_tool = ArgoCDTool(argocd_server=argocd_server)
            self.has_argocd = True
        except ValueError:
            # ArgoCD tool not available - will rely on git and kubernetes only
            self.has_argocd = False
            
        self.kube_tool = KubeDeploymentTool()
        
        # Define tools list based on what's available
        tools = [self.git_tool.execute, self.git_tool.get_diff, self.kube_tool.execute]
        if self.has_argocd:
            tools.extend([self.argocd_tool.execute, self.argocd_tool.get_application_status])
        
        # Create a crewAI agent for deployment analysis
        self.deployment_analyzer = Agent(
            role="Deployment Analyzer",
            goal="Analyze deployment configurations and identify recent changes",
            backstory="You are an expert at analyzing deployment configurations and identifying problematic changes.",
            verbose=True,
            llm=self.llm,
            tools=tools
        )

    def _get_deployment_data(self, alert_data):
        """Collect relevant deployment data for the alert"""
        deployment_data = {}
        
        try:
            # Extract service/app and namespace from alert if available
            service = alert_data.get('labels', {}).get('service')
            namespace = alert_data.get('labels', {}).get('namespace', 'default')
            deployment = alert_data.get('labels', {}).get('deployment', service)
            
            # Get Git repository changes
            deployment_data['git_changes'] = self.git_tool.execute(
                repo_path=self.git_repo_path,
                since="1 day ago",
                max_commits=20
            )
            
            # If we found commits, get the diff for the latest one
            if 'commits' in deployment_data['git_changes'] and deployment_data['git_changes']['commits']:
                latest_commit = deployment_data['git_changes']['commits'][0]
                deployment_data['latest_commit_diff'] = self.git_tool.get_diff(
                    repo_path=self.git_repo_path,
                    commit_hash=latest_commit['hash']
                )
            
            # Get Kubernetes deployment info if we have service/deployment name
            if deployment:
                deployment_data['kubernetes_deployment'] = self.kube_tool.execute(
                    namespace=namespace,
                    deployment_name=deployment
                )
            
            # Get ArgoCD data if available and we have service name
            if self.has_argocd and service:
                try:
                    deployment_data['argocd_history'] = self.argocd_tool.execute(
                        app_name=service,
                        limit=10
                    )
                    deployment_data['argocd_status'] = self.argocd_tool.get_application_status(
                        app_name=service
                    )
                except Exception as e:
                    deployment_data['argocd_error'] = str(e)
            
        except Exception as e:
            deployment_data['error'] = str(e)
            
        return deployment_data

    def analyze_deployment_config(self, alert_data):
        """Analyze deployment configuration changes using crewAI"""
        # First collect relevant deployment data
        deployment_data = self._get_deployment_data(alert_data)
        
        # Extract service/app and namespace from alert for context
        service = alert_data.get('labels', {}).get('service', 'unknown')
        namespace = alert_data.get('labels', {}).get('namespace', 'default')
        alert_name = alert_data.get('labels', {}).get('alertname', 'unknown')
        alert_summary = alert_data.get('annotations', {}).get('summary', '')
        
        # Create task for deployment analysis
        analysis_task = Task(
            description=f"""
            Analyze the following deployment data to identify recent changes that may have caused issues:
            {json.dumps(deployment_data)}
            
            Alert Information:
            Service: {service}
            Namespace: {namespace}
            Alert Name: {alert_name}
            Summary: {alert_summary}
            
            Focus your analysis on:
            1. Recent deployment changes in Git or ArgoCD that correlate with the timing of the alert
            2. Configuration issues in Kubernetes deployments
            3. Version changes that might have introduced bugs
            4. Resource constraints (CPU/memory limits) that may affect performance
            
            Provide specific evidence connecting deployment changes to the observed issue.
            """,
            agent=self.deployment_analyzer,
            expected_output="A detailed analysis of deployment configuration changes and potential issues"
        )
        
        # Create a crew with the deployment analyzer agent
        crew = Crew(
            agents=[self.deployment_analyzer],
            tasks=[analysis_task],
            verbose=True
        )
        
        # Execute the crew to analyze the deployment
        result = crew.kickoff()
        return result, deployment_data

    def listen(self):
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("deployment_agent")
        print("[DeploymentAgent] Listening for messages...")
        
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        alert = json.loads(message['data'])
                        print(f"[DeploymentAgent] Processing alert: {alert}")
                        
                        # Use crewAI to analyze the deployment
                        analysis_result, deployment_data = self.analyze_deployment_config(alert)
                        
                        # Determine what type of deployment issue was observed
                        observed_issue = self._determine_observed_issue(alert, deployment_data)
                        
                        # Prepare result for the orchestrator
                        result = {
                            "agent": "deployment", 
                            "observed": observed_issue,
                            "analysis": str(analysis_result),
                            "alert_id": alert.get("alert_id", "unknown")
                        }
                        
                        print(f"[DeploymentAgent] Sending analysis for alert ID: {result['alert_id']}")
                        self.redis_client.publish("orchestrator_response", json.dumps(result))
                    except Exception as e:
                        print(f"[DeploymentAgent] Error processing message: {str(e)}")
        except redis.RedisError as e:
            print(f"[DeploymentAgent] Redis connection error: {str(e)}")
            # Try to reconnect
            self.redis_client = redis.Redis(host='redis', port=6379)
            self.listen()  # Recursive call to restart listening
            
    def _determine_observed_issue(self, alert, deployment_data):
        """Determine the type of deployment issue observed based on alert and deployment data"""
        # Default observation
        observed_issue = "recent_config_change"
        
        # Check for specific conditions in deployment data
        
        # Check for git changes
        git_changes = deployment_data.get('git_changes', {})
        if 'commits' in git_changes and git_changes['commits']:
            # We have recent commits
            observed_issue = "recent_git_change"
            
            # Check commit messages for keywords
            for commit in git_changes['commits'][:3]:  # Check the most recent 3 commits
                message = commit.get('message', '').lower()
                if 'fix' in message or 'bug' in message:
                    observed_issue = "recent_bugfix_deployment"
                elif 'config' in message or 'configuration' in message:
                    observed_issue = "recent_config_change"
                elif 'version' in message or 'upgrade' in message or 'update' in message:
                    observed_issue = "version_upgrade"
        
        # Check for ArgoCD deployments
        argocd_history = deployment_data.get('argocd_history', {})
        if argocd_history and argocd_history.get('deployments'):
            # We have recent ArgoCD deployments, this takes precedence
            observed_issue = "recent_argocd_deployment"
        
        # Check for Kubernetes deployment issues
        k8s_deployment = deployment_data.get('kubernetes_deployment', {})
        if k8s_deployment:
            # Check for resource constraints
            if k8s_deployment.get('resource_issues'):
                observed_issue = "resource_constraint"
            
            # Check for replica mismatches 
            if k8s_deployment.get('available_replicas', 0) < k8s_deployment.get('desired_replicas', 1):
                observed_issue = "pod_availability_issue"
            
            # Check for pending status
            if k8s_deployment.get('status') == 'Pending':
                observed_issue = "deployment_pending"
                
        return observed_issue