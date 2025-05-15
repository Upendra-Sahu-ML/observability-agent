"""
Kubernetes tools for querying pod, deployment, and service information
"""
import os
import logging
import json
import subprocess
from kubernetes import client, config
from crewai.tools import tool

# Configure logging
logger = logging.getLogger(__name__)

class KubernetesTools:
    """Collection of tools for working with Kubernetes resources"""
    
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
            self.apps_api = client.AppsV1Api()
            
        except Exception as e:
            logger.error(f"Error initializing Kubernetes client: {str(e)}")
            # Don't raise immediately - allow CLI fallback for tools
            self.core_api = None
            self.apps_api = None
    
    @tool("Get information about Kubernetes pods in a namespace")
    def get_pods(self, namespace, label_selector=None, field_selector=None):
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
            if self.core_api:
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
            else:
                # Fallback to kubectl
                cmd = ["kubectl", "get", "pods", "-n", namespace, "-o", "json"]
                
                if label_selector:
                    cmd.extend(["-l", label_selector])
                    
                if field_selector:
                    cmd.extend(["--field-selector", field_selector])
                    
                pod_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
                return json.loads(pod_output)
                
        except Exception as e:
            logger.error(f"Error getting pod information: {str(e)}")
            return {"error": str(e)}
    
    @tool("Get logs from a specific Kubernetes pod")
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
            if self.core_api:
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
            else:
                # Fallback to kubectl
                cmd = ["kubectl", "logs", pod_name, "-n", namespace]
                
                if container:
                    cmd.extend(["-c", container])
                    
                if tail_lines:
                    cmd.extend(["--tail", str(tail_lines)])
                    
                log_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
                
                return {
                    "namespace": namespace,
                    "pod": pod_name,
                    "container": container,
                    "logs": log_output
                }
                
        except Exception as e:
            logger.error(f"Error getting pod logs: {str(e)}")
            return {"error": str(e)}
    
    @tool("Get information about Kubernetes deployments in a namespace")
    def get_deployments(self, namespace, deployment_name=None):
        """
        Get information about deployments in a namespace
        
        Args:
            namespace (str): Kubernetes namespace
            deployment_name (str, optional): Name of a specific deployment to query
            
        Returns:
            dict: Information about deployments in the namespace
        """
        try:
            if self.apps_api:
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
            else:
                # Fallback to kubectl
                cmd = ["kubectl", "get", "deployments", "-n", namespace, "-o", "json"]
                
                if deployment_name:
                    cmd[2] = "deployment"
                    cmd.insert(3, deployment_name)
                    
                deployment_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
                return json.loads(deployment_output)
                
        except Exception as e:
            logger.error(f"Error getting deployment information: {str(e)}")
            return {"error": str(e)}
    
    @tool("Get events related to a Kubernetes deployment")
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
            # Use kubectl to get events as it's more straightforward
            cmd = ["kubectl", "get", "events", "-n", namespace, "--field-selector", f"involvedObject.name={deployment_name}", "-o", "json"]
            events_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            events_data = json.loads(events_output)
            
            # Also get events for pods managed by this deployment
            cmd_get_deploy = ["kubectl", "get", "deployment", deployment_name, "-n", namespace, "-o", "json"]
            deploy_output = subprocess.check_output(cmd_get_deploy, stderr=subprocess.STDOUT, universal_newlines=True)
            deploy_data = json.loads(deploy_output)
            
            # Get the deployment's selector
            selector = deploy_data.get("spec", {}).get("selector", {}).get("matchLabels", {})
            selector_str = ",".join([f"{k}={v}" for k, v in selector.items()])
            
            # Get pods matching the selector
            cmd_get_pods = ["kubectl", "get", "pods", "-n", namespace, "-l", selector_str, "-o", "json"]
            pods_output = subprocess.check_output(cmd_get_pods, stderr=subprocess.STDOUT, universal_newlines=True)
            pods_data = json.loads(pods_output)
            
            # Get events for each pod
            pod_events = []
            for pod in pods_data.get("items", []):
                pod_name = pod.get("metadata", {}).get("name")
                cmd_pod_events = ["kubectl", "get", "events", "-n", namespace, "--field-selector", f"involvedObject.name={pod_name}", "-o", "json"]
                pod_events_output = subprocess.check_output(cmd_pod_events, stderr=subprocess.STDOUT, universal_newlines=True)
                pod_events_data = json.loads(pod_events_output)
                pod_events.extend(pod_events_data.get("items", []))
            
            # Combine and format all events
            all_events = events_data.get("items", []) + pod_events
            
            result = {
                "namespace": namespace,
                "deployment": deployment_name,
                "event_count": len(all_events),
                "events": []
            }
            
            for event in all_events:
                event_info = {
                    "type": event.get("type"),
                    "reason": event.get("reason"),
                    "message": event.get("message"),
                    "count": event.get("count"),
                    "first_timestamp": event.get("firstTimestamp"),
                    "last_timestamp": event.get("lastTimestamp"),
                    "involved_object": {
                        "kind": event.get("involvedObject", {}).get("kind"),
                        "name": event.get("involvedObject", {}).get("name")
                    }
                }
                result["events"].append(event_info)
            
            # Sort events by timestamp (newest first)
            result["events"].sort(key=lambda x: x["last_timestamp"] if x["last_timestamp"] else "", reverse=True)
            
            return result
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting deployment events: {str(e)}")
            return {"error": str(e), "output": e.output}
    
    @tool("Check Kubernetes service status and endpoints")
    def get_service(self, namespace, service_name):
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
    
    @tool("Get resource usage metrics for Kubernetes pods")
    def get_pod_metrics(self, namespace, pod_name=None, label_selector=None):
        """
        Get resource usage metrics for pods using the Kubernetes Metrics API
        
        Args:
            namespace (str): Kubernetes namespace
            pod_name (str, optional): Name of a specific pod
            label_selector (str, optional): Label selector to filter pods
            
        Returns:
            dict: Pod metrics information
        """
        try:
            # Check if metrics-server is available using kubectl top
            if pod_name:
                cmd = ["kubectl", "top", "pod", pod_name, "-n", namespace, "--no-headers"]
            else:
                cmd = ["kubectl", "top", "pods", "-n", namespace, "--no-headers"]
                
            if label_selector:
                cmd.extend(["-l", label_selector])
                
            metrics_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            
            # Parse the output
            result = {
                "namespace": namespace,
                "pods": []
            }
            
            for line in metrics_output.strip().split('\n'):
                if not line:
                    continue
                    
                parts = line.split()
                if len(parts) >= 3:
                    pod_metrics = {
                        "name": parts[0],
                        "cpu": parts[1],
                        "memory": parts[2]
                    }
                    result["pods"].append(pod_metrics)
            
            result["pod_count"] = len(result["pods"])
            return result
                
        except subprocess.CalledProcessError as e:
            if "metrics not available yet" in e.output:
                return {"error": "Metrics not available yet. The metrics server may need more time to collect data."}
            else:
                logger.error(f"Error getting pod metrics: {str(e)}")
                return {"error": str(e), "output": e.output}
    
    @tool("Get information about available Kubernetes namespaces")
    def get_namespaces(self):
        """
        Get information about available Kubernetes namespaces
        
        Returns:
            dict: Information about available namespaces
        """
        try:
            cmd = ["kubectl", "get", "namespaces", "-o", "json"]
            ns_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            ns_data = json.loads(ns_output)
            
            result = {
                "namespace_count": len(ns_data.get("items", [])),
                "namespaces": []
            }
            
            for ns in ns_data.get("items", []):
                ns_info = {
                    "name": ns.get("metadata", {}).get("name"),
                    "status": ns.get("status", {}).get("phase"),
                    "creation_timestamp": ns.get("metadata", {}).get("creationTimestamp"),
                    "labels": ns.get("metadata", {}).get("labels", {})
                }
                result["namespaces"].append(ns_info)
            
            return result
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting namespaces: {str(e)}")
            return {"error": str(e), "output": e.output}
    
    @tool("Get status of all Kubernetes nodes in the cluster")
    def get_nodes(self):
        """
        Get status of all Kubernetes nodes in the cluster
        
        Returns:
            dict: Information about all nodes
        """
        try:
            cmd = ["kubectl", "get", "nodes", "-o", "json"]
            nodes_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            nodes_data = json.loads(nodes_output)
            
            result = {
                "node_count": len(nodes_data.get("items", [])),
                "nodes": []
            }
            
            for node in nodes_data.get("items", []):
                # Extract node conditions
                conditions = {}
                for condition in node.get("status", {}).get("conditions", []):
                    conditions[condition.get("type")] = {
                        "status": condition.get("status"),
                        "reason": condition.get("reason"),
                        "message": condition.get("message"),
                        "last_transition_time": condition.get("lastTransitionTime")
                    }
                
                # Extract capacity and allocatable resources
                capacity = node.get("status", {}).get("capacity", {})
                allocatable = node.get("status", {}).get("allocatable", {})
                
                node_info = {
                    "name": node.get("metadata", {}).get("name"),
                    "labels": node.get("metadata", {}).get("labels", {}),
                    "creation_timestamp": node.get("metadata", {}).get("creationTimestamp"),
                    "conditions": conditions,
                    "resources": {
                        "capacity": {
                            "cpu": capacity.get("cpu"),
                            "memory": capacity.get("memory"),
                            "pods": capacity.get("pods")
                        },
                        "allocatable": {
                            "cpu": allocatable.get("cpu"),
                            "memory": allocatable.get("memory"),
                            "pods": allocatable.get("pods")
                        }
                    },
                    "kubelet_version": node.get("status", {}).get("nodeInfo", {}).get("kubeletVersion"),
                    "os_image": node.get("status", {}).get("nodeInfo", {}).get("osImage"),
                    "architecture": node.get("status", {}).get("nodeInfo", {}).get("architecture")
                }
                
                result["nodes"].append(node_info)
            
            return result
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting nodes: {str(e)}")
            return {"error": str(e), "output": e.output}