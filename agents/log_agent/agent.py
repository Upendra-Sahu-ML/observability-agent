import redis
import json
import os
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from common.tools.log_tools import (
    LokiQueryTool,
    PodLogTool,
    FileLogTool
)

load_dotenv()

class LogAgent:
    def __init__(self, loki_url="http://loki:3100", log_directory="/var/log"):
        self.redis_client = redis.Redis(host='redis', port=6379)
        self.log_directory = log_directory
        
        # Initialize OpenAI model
        self.llm = ChatOpenAI(model="gpt-4")
        
        # Initialize Log tools
        self.loki_query_tool = LokiQueryTool(loki_url=loki_url)
        self.pod_log_tool = PodLogTool()
        self.file_log_tool = FileLogTool()
        
        # Create a crewAI agent for log analysis
        self.log_analyzer = Agent(
            role="Log Analyst",
            goal="Analyze logs to detect patterns and identify issues",
            backstory="You are an expert at analyzing log data and identifying critical patterns that could indicate system problems.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.loki_query_tool.execute,
                self.pod_log_tool.execute,
                self.file_log_tool.execute
            ]
        )

    def _get_logs_for_alert(self, alert_data):
        """Collect relevant logs for the alert"""
        logs_data = {}
        
        try:
            # Extract service/app and namespace from alert if available
            service = alert_data.get('labels', {}).get('service')
            namespace = alert_data.get('labels', {}).get('namespace', 'default')
            pod_name_pattern = alert_data.get('labels', {}).get('pod', '')
            
            # Get time range from alert or use a default
            end_time = alert_data.get('startsAt', None)
            # Look at logs from 15 minutes before the alert
            start_time = None
            if end_time:
                from datetime import datetime, timedelta
                try:
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    start_time = (end_dt - timedelta(minutes=15)).isoformat() + 'Z'
                except:
                    pass
            
            # Query Loki for logs if service is available
            if service:
                loki_query = f'{{service="{service}"}}'
                logs_data['loki_logs'] = self.loki_query_tool.execute(
                    query=loki_query,
                    start=start_time,
                    end=end_time,
                    limit=500
                )
            
            # Try to get pod logs if pod name pattern is available
            if pod_name_pattern:
                try:
                    # Use selector based approach for pattern
                    selector = f"app={service}" if service else None
                    
                    # If we have a specific pod name, use it directly
                    if pod_name_pattern and not pod_name_pattern.endswith('*'):
                        logs_data['pod_logs'] = self.pod_log_tool.execute(
                            namespace=namespace,
                            pod_name=pod_name_pattern,
                            since="15m" if not start_time else None,
                            tail=500
                        )
                    elif selector:
                        # Otherwise use selector
                        logs_data['pod_logs'] = self.pod_log_tool.execute(
                            namespace=namespace,
                            selector=selector,
                            since="15m" if not start_time else None,
                            tail=500
                        )
                except Exception as e:
                    logs_data['pod_logs_error'] = str(e)
            
            # Try to get application logs from standard locations
            if service:
                try:
                    app_log_path = os.path.join(self.log_directory, f"{service}.log")
                    logs_data['app_logs'] = self.file_log_tool.execute(
                        file_path=app_log_path,
                        tail=200
                    )
                except Exception as e:
                    logs_data['app_logs_error'] = str(e)
            
            # Always try to get system logs
            try:
                logs_data['system_logs'] = self.file_log_tool.execute(
                    file_path="/var/log/syslog",
                    tail=100
                )
            except Exception as e:
                logs_data['system_logs_error'] = str(e)
            
        except Exception as e:
            logs_data['error'] = str(e)
            
        return logs_data

    def analyze_logs(self, alert_data):
        """Analyze logs using crewAI"""
        # First collect relevant log data
        logs_data = self._get_logs_for_alert(alert_data)
        
        # Extract context from alert
        service = alert_data.get('labels', {}).get('service', 'unknown')
        alert_name = alert_data.get('labels', {}).get('alertname', 'unknown')
        alert_summary = alert_data.get('annotations', {}).get('summary', '')
        
        # Create task for log analysis
        analysis_task = Task(
            description=f"""
            Analyze the following log data to identify issues related to the alert:
            {json.dumps(logs_data)}
            
            Alert Information:
            Service: {service}
            Alert Name: {alert_name}
            Summary: {alert_summary}
            
            Focus your analysis on:
            1. Error messages and stack traces
            2. Repeated patterns of failures
            3. Unusual behavior preceding the alert
            4. Application crashes or restarts
            5. System resource issues mentioned in logs
            
            Provide specific evidence from the logs that explains what caused the alert.
            """,
            agent=self.log_analyzer,
            expected_output="A detailed analysis of logs and identification of potential issues"
        )
        
        # Create a crew with the log analyzer agent
        crew = Crew(
            agents=[self.log_analyzer],
            tasks=[analysis_task],
            verbose=True
        )
        
        # Execute the crew to analyze the logs
        result = crew.kickoff()
        return result, logs_data

    def listen(self):
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("log_agent")
        print("[LogAgent] Listening for messages...")
        
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        alert = json.loads(message['data'])
                        print(f"[LogAgent] Processing alert: {alert}")
                        
                        # Use crewAI to analyze the logs
                        analysis_result, logs_data = self.analyze_logs(alert)
                        
                        # Determine what type of log issue was observed
                        observed_issue = self._determine_observed_issue(alert, logs_data, analysis_result)
                        
                        # Prepare result for the orchestrator
                        result = {
                            "agent": "log", 
                            "observed": observed_issue,
                            "analysis": str(analysis_result),
                            "alert_id": alert.get("alert_id", "unknown")
                        }
                        
                        print(f"[LogAgent] Sending analysis for alert ID: {result['alert_id']}")
                        self.redis_client.publish("orchestrator_response", json.dumps(result))
                    except Exception as e:
                        print(f"[LogAgent] Error processing message: {str(e)}")
        except redis.RedisError as e:
            print(f"[LogAgent] Redis connection error: {str(e)}")
            # Try to reconnect
            import time
            time.sleep(5)
            print("[LogAgent] Attempting to reconnect to Redis...")
            self.redis_client = redis.Redis(host='redis', port=6379)
            self.listen()  # Recursive call to restart listening
    
    def _determine_observed_issue(self, alert, logs_data, analysis_result):
        """Determine the type of log issue observed based on logs and alert data"""
        # Default observation
        observed_issue = "unknown_log_issue"
        
        # First check the alert name for hints
        alert_name = alert.get('labels', {}).get('alertname', '').lower()
        if 'crash' in alert_name or 'restart' in alert_name:
            observed_issue = "crash_loop_detected"
        elif 'memory' in alert_name:
            observed_issue = "memory_leak_detected"
        elif 'disk' in alert_name:
            observed_issue = "disk_space_issue"
        elif 'error' in alert_name:
            observed_issue = "application_error"
            
        # Check log data for specific patterns
        loki_logs = logs_data.get('loki_logs', {}).get('lines', [])
        pod_logs = logs_data.get('pod_logs', {}).get('logs', '')
        app_logs = logs_data.get('app_logs', {}).get('content', '')
        
        # Combine all logs for pattern detection
        all_logs = '\n'.join([
            '\n'.join([line.get('line', '') for line in loki_logs]),
            pod_logs,
            app_logs
        ])
        
        # Look for common error patterns
        if 'OutOfMemoryError' in all_logs or 'memory limit exceeded' in all_logs:
            observed_issue = "memory_limit_exceeded"
        elif 'CrashLoopBackOff' in all_logs:
            observed_issue = "crash_loop_detected"
        elif 'OOMKilled' in all_logs:
            observed_issue = "out_of_memory_killed"
        elif 'connection refused' in all_logs.lower() or 'connection timeout' in all_logs.lower():
            observed_issue = "connection_failure"
        elif 'exception' in all_logs.lower() and 'stack trace' in all_logs.lower():
            observed_issue = "application_exception"
        elif 'authentication failed' in all_logs.lower() or 'access denied' in all_logs.lower():
            observed_issue = "authentication_failure"
        elif 'warning' in all_logs.lower() and not ('error' in all_logs.lower() or 'exception' in all_logs.lower()):
            observed_issue = "application_warning"
            
        # Convert analysis_result to string for pattern matching if not already
        analysis_str = str(analysis_result)
        
        # Check if analysis specifically calls out certain issues
        if 'memory leak' in analysis_str.lower():
            observed_issue = "memory_leak_detected"
        elif 'database' in analysis_str.lower() and ('timeout' in analysis_str.lower() or 'connection' in analysis_str.lower()):
            observed_issue = "database_connection_issue"
            
        return observed_issue