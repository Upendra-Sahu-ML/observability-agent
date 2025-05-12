"""
Kubernetes tools for querying pod, deployment, and service information
"""
import os
import logging
import json
import subprocess
from kubernetes import client, config
from common.tools.base import AgentTool

# Configure logging
logger = logging.getLogger(__name__)

class KubePodTool(AgentTool):
    """Tool for getting information about Kubernetes pods"""
    
    def __init__(self, kubeconfig_path=None, in_cluster=True):
        """
        Initialize Kubernetes client
        
        Args:
            kubeconfig_path (str, optional): Path to kubeconfig file
            in_cluster (bool): Whether to use in-cluster configuration
        """
        try:
            if in_cluster:
                config.load_incluster_config()
                logger.info("Using in-cluster Kubernetes configuration")
            elif kubeconfig_path:
                config.load_kube_config(config_file=kubeconfig_path)
                logger.info(f"Using kubeconfig from {kubeconfig_path}")
            else:
                config.load_kube_config()
                logger.info("Using default kubeconfig")
                
            self.core_api = client.CoreV1Api()
            
        except Exception as e:
            logger.error(f"Error initializing Kubernetes client: {str(e)}")
            raise
    
    @property
    def name(self):
        return "kube_pods"
    
    @property
    def description(self):
        return "Get information about Kubernetes pods in a namespace"
    
    def execute(self, namespace, label_selector=None, field_selector=None):
        """
        Get information about pods in a namespace
        
        Args:
            namespace (str): Kubernetes namespace
            label_selector (str, optional): Label selector (e.g. 'app=myapp')
            field_selector (str, optional): Field selector (e.g. 'status.phase=Running')
            
        Returns:
            dict: Information about pods in the namespace
        """
        try:
            pods = self.core_api.list_namespaced_pod(
                namespace=namespace,
                label_selector=label_selector,
                field_selector=field_selector
            )
            
            result = {
                "namespace": namespace,
                "pod_count": len(pods.items),
                "pods": []
            }
            
            for pod in pods.items:
                pod_info = {
                    "name": pod.metadata.name,
                    "status": pod.status.phase,
                    "creation_timestamp": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None,
                    "node": pod.spec.node_name,
                    "ip": pod.status.pod_ip,
                    "containers": [],
                    "conditions": []
                }
                
                # Add container information
                if pod.status.container_statuses:
                    for container in pod.status.container_statuses:
                        container_info = {
                            "name": container.name,
                            "ready": container.ready,
                            "restart_count": container.restart_count,
                            "image": container.image
                        }
                        
                        # Add container state
                        if container.state.running:
                            container_info["state"] = "running"
                            container_info["started_at"] = container.state.running.started_at.isoformat() if container.state.running.started_at else None
                        elif container.state.waiting:
                            container_info["state"] = "waiting"
                            container_info["reason"] = container.state.waiting.reason
                            container_info["message"] = container.state.waiting.message
                        elif container.state.terminated:
                            container_info["state"] = "terminated"
                            container_info["reason"] = container.state.terminated.reason
                            container_info["exit_code"] = container.state.terminated.exit_code
                            
                        pod_info["containers"].append(container_info)
                
                # Add pod conditions
                if pod.status.conditions:
                    for condition in pod.status.conditions:
                        pod_info["conditions"].append({
                            "type": condition.type,
                            "status": condition.status,
                            "last_transition_time": condition.last_transition_time.isoformat() if condition.last_transition_time else None,
                            "reason": condition.reason,
                            "message": condition.message
                        })
                
                result["pods"].append(pod_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting pod information: {str(e)}")
            return {"error": str(e)}
    
    def get_pod_logs(self, namespace, pod_name, container=None, tail_lines=100):
        """
        Get logs from a specific pod
        
        Args:
            namespace (str): Kubernetes namespace
            pod_name (str): Name of the pod
            container (str, optional): Container name (if pod has multiple containers)
            tail_lines (int, optional): Number of lines to return from the end of the logs
            
        Returns:
            dict: Pod logs
        """
        try:
            logs = self.core_api.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                container=container,
                tail_lines=tail_lines
            )
            
            return {
                "namespace": namespace,
                "pod": pod_name,
                "container": container,
                "logs": logs
            }
            
        except Exception as e:
            logger.error(f"Error getting pod logs: {str(e)}")
            return {"error": str(e)}

class KubeDeploymentTool(AgentTool):
    """Tool for getting information about Kubernetes deployments"""
    
    def __init__(self, kubeconfig_path=None, in_cluster=True):
        """
        Initialize Kubernetes client
        
        Args:
            kubeconfig_path (str, optional): Path to kubeconfig file
            in_cluster (bool): Whether to use in-cluster configuration
        """
        try:
            if in_cluster:
                config.load_incluster_config()
                logger.info("Using in-cluster Kubernetes configuration")
            elif kubeconfig_path:
                config.load_kube_config(config_file=kubeconfig_path)
                logger.info(f"Using kubeconfig from {kubeconfig_path}")
            else:
                config.load_kube_config()
                logger.info("Using default kubeconfig")
                
            self.apps_api = client.AppsV1Api()
            self.core_api = client.CoreV1Api()
            
        except Exception as e:
            logger.error(f"Error initializing Kubernetes client: {str(e)}")
            raise
    
    @property
    def name(self):
        return "kube_deployments"
    
    @property
    def description(self):
        return "Get information about Kubernetes deployments in a namespace"
    
    def execute(self, namespace, deployment_name=None):
        """
        Get information about deployments in a namespace
        
        Args:
            namespace (str): Kubernetes namespace
            deployment_name (str, optional): Name of a specific deployment to query
            
        Returns:
            dict: Information about deployments in the namespace
        """
        try:
            if deployment_name:
                # Get a specific deployment
                deployment = self.apps_api.read_namespaced_deployment(
                    name=deployment_name,
                    namespace=namespace
                )
                deployments = [deployment]
            else:
                # Get all deployments in the namespace
                deployments_list = self.apps_api.list_namespaced_deployment(namespace=namespace)
                deployments = deployments_list.items
            
            result = {
                "namespace": namespace,
                "deployment_count": len(deployments),
                "deployments": []
            }
            
            for deployment in deployments:
                deployment_info = {
                    "name": deployment.metadata.name,
                    "replicas": {
                        "desired": deployment.spec.replicas,
                        "available": deployment.status.available_replicas,
                        "ready": deployment.status.ready_replicas,
                        "unavailable": deployment.status.unavailable_replicas
                    },
                    "selector": deployment.spec.selector.match_labels,
                    "strategy": deployment.spec.strategy.type,
                    "creation_timestamp": deployment.metadata.creation_timestamp.isoformat() if deployment.metadata.creation_timestamp else None,
                    "conditions": []
                }
                
                # Add container information
                containers = []
                if deployment.spec.template.spec.containers:
                    for container in deployment.spec.template.spec.containers:
                        container_info = {
                            "name": container.name,
                            "image": container.image,
                            "ports": []
                        }
                        
                        # Add port information
                        if container.ports:
                            for port in container.ports:
                                container_info["ports"].append({
                                    "container_port": port.container_port,
                                    "protocol": port.protocol
                                })
                        
                        # Add resource requirements if specified
                        if container.resources:
                            container_info["resources"] = {
                                "limits": container.resources.limits,
                                "requests": container.resources.requests
                            }
                            
                        containers.append(container_info)
                
                deployment_info["containers"] = containers
                
                # Add deployment conditions
                if deployment.status.conditions:
                    for condition in deployment.status.conditions:
                        deployment_info["conditions"].append({
                            "type": condition.type,
                            "status": condition.status,
                            "last_update_time": condition.last_update_time.isoformat() if condition.last_update_time else None,
                            "last_transition_time": condition.last_transition_time.isoformat() if condition.last_transition_time else None,
                            "reason": condition.reason,
                            "message": condition.message
                        })
                
                result["deployments"].append(deployment_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting deployment information: {str(e)}")
            return {"error": str(e)}
    
    def get_deployment_events(self, namespace, deployment_name):
        """
        Get events related to a deployment
        
        Args:
            namespace (str): Kubernetes namespace
            deployment_name (str): Name of the deployment
            
        Returns:
            dict: Events related to the deployment
        """
        try:
            # Get the deployment to extract its selector
            deployment = self.apps_api.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace
            )
            
            # Get all events in the namespace
            field_selector = f"involvedObject.name={deployment_name},involvedObject.namespace={namespace}"
            events = self.core_api.list_namespaced_event(
                namespace=namespace,
                field_selector=field_selector
            )
            
            # Get events for the deployment's pods
            pods = self.core_api.list_namespaced_pod(
                namespace=namespace,
                label_selector=",".join([f"{k}={v}" for k, v in deployment.spec.selector.match_labels.items()])
            )
            
            pod_names = [pod.metadata.name for pod in pods.items]
            pod_events = []
            
            for pod_name in pod_names:
                pod_field_selector = f"involvedObject.name={pod_name},involvedObject.namespace={namespace}"
                pod_event_list = self.core_api.list_namespaced_event(
                    namespace=namespace,
                    field_selector=pod_field_selector
                )
                pod_events.extend(pod_event_list.items)
            
            # Combine all events
            all_events = events.items + pod_events
            
            # Format the events
            result = {
                "namespace": namespace,
                "deployment": deployment_name,
                "event_count": len(all_events),
                "events": []
            }
            
            for event in all_events:
                result["events"].append({
                    "type": event.type,
                    "reason": event.reason,
                    "message": event.message,
                    "count": event.count,
                    "first_timestamp": event.first_timestamp.isoformat() if event.first_timestamp else None,
                    "last_timestamp": event.last_timestamp.isoformat() if event.last_timestamp else None,
                    "involved_object": {
                        "kind": event.involved_object.kind,
                        "name": event.involved_object.name
                    }
                })
            
            # Sort events by timestamp (newest first)
            result["events"].sort(key=lambda x: x["last_timestamp"] if x["last_timestamp"] else "", reverse=True)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting deployment events: {str(e)}")
            return {"error": str(e)}

class KubeServiceTool(AgentTool):
    """Tool for checking Kubernetes service status and endpoints"""
    
    @property
    def name(self):
        return "kube_service"
    
    @property
    def description(self):
        return "Check Kubernetes service status and endpoints"
    
    def execute(self, namespace, service_name):
        """
        Get information about a Kubernetes service including endpoints
        
        Args:
            namespace (str): Kubernetes namespace
            service_name (str): Name of the service
            
        Returns:
            dict: Service status and endpoints information
        """
        result = {}
        
        try:
            # Get service details
            cmd_service = ["kubectl", "get", "service", service_name, "-n", namespace, "-o", "json"]
            service_output = subprocess.check_output(cmd_service, stderr=subprocess.STDOUT, universal_newlines=True)
            service_data = json.loads(service_output)
            
            # Get endpoints for the service
            cmd_endpoints = ["kubectl", "get", "endpoints", service_name, "-n", namespace, "-o", "json"]
            endpoints_output = subprocess.check_output(cmd_endpoints, stderr=subprocess.STDOUT, universal_newlines=True)
            endpoints_data = json.loads(endpoints_output)
            
            # Process service data
            service_info = {
                "name": service_data.get("metadata", {}).get("name"),
                "namespace": service_data.get("metadata", {}).get("namespace"),
                "type": service_data.get("spec", {}).get("type"),
                "cluster_ip": service_data.get("spec", {}).get("clusterIP"),
                "ports": service_data.get("spec", {}).get("ports", []),
                "selector": service_data.get("spec", {}).get("selector", {})
            }
            
            # Process endpoints data
            endpoints_info = {
                "name": endpoints_data.get("metadata", {}).get("name"),
                "namespace": endpoints_data.get("metadata", {}).get("namespace"),
                "subsets": []
            }
            
            for subset in endpoints_data.get("subsets", []):
                addresses = subset.get("addresses", [])
                ports = subset.get("ports", [])
                
                subset_info = {
                    "address_count": len(addresses),
                    "addresses": [{"ip": addr.get("ip"), "hostname": addr.get("hostname"), "node": addr.get("nodeName")} for addr in addresses],
                    "ports": [{"name": port.get("name"), "port": port.get("port"), "protocol": port.get("protocol")} for port in ports]
                }
                
                endpoints_info["subsets"].append(subset_info)
            
            result["service"] = service_info
            result["endpoints"] = endpoints_info
            
            return result
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting service information: {str(e)}")
            return {"error": str(e), "output": e.output}