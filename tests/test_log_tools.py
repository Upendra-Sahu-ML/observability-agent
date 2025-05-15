import os
import pytest
import json
from unittest.mock import Mock, patch, MagicMock, call

class TestLokiQueryTool:
    def test_init(self):
        """Test the initialization of LokiQueryTool"""
        from common.tools.log_tools import LokiQueryTool
        
        # Test with default URL
        tool = LokiQueryTool()
        assert tool.base_url == "http://loki:3100"
        assert tool.api_path == "/loki/api/v1/"
        
        # Test with custom URL
        custom_url = "http://custom-loki:9000"
        tool = LokiQueryTool(loki_url=custom_url)
        assert tool.base_url == custom_url
    
    def test_name_and_description(self):
        """Test name and description properties"""
        from common.tools.log_tools import LokiQueryTool
        
        tool = LokiQueryTool()
        assert tool.name == "loki_query"
        assert tool.description == "Query logs from Loki using LogQL"
    
    @patch('common.tools.log_tools.requests.get')
    def test_execute(self, mock_get):
        """Test executing a LogQL query"""
        from common.tools.log_tools import LokiQueryTool
        
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "result": [
                    {
                        "stream": {"app": "test-app"},
                        "values": [["1620000000000000000", "log line 1"]]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        # Create tool and execute query
        tool = LokiQueryTool()
        result = tool.execute(query='{app="test-app"}', limit=10)
        
        # Verify request
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "http://loki:3100/loki/api/v1/query_range" == args[0]
        assert kwargs['params']['query'] == '{app="test-app"}'
        assert kwargs['params']['limit'] == 10
        assert kwargs['params']['direction'] == "backward"
        
        # Verify result
        assert result == mock_response.json.return_value["data"]
    
    @patch('common.tools.log_tools.requests.get')
    def test_execute_error(self, mock_get):
        """Test error handling in execute method"""
        from common.tools.log_tools import LokiQueryTool
        
        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_get.return_value = mock_response
        
        # Create tool and verify exception
        tool = LokiQueryTool()
        with pytest.raises(Exception) as excinfo:
            tool.execute(query='{app="test-app"}')
        
        assert "Loki query failed with status 400" in str(excinfo.value)
    
    @patch('common.tools.log_tools.LokiQueryTool.execute')
    def test_get_error_patterns(self, mock_execute):
        """Test get_error_patterns method"""
        from common.tools.log_tools import LokiQueryTool
        
        # Mock execute response
        mock_execute.return_value = {
            "result": [
                {
                    "stream": {"app": "test-app"},
                    "values": [
                        ["1620000000000000000", "Error: Connection refused"],
                        ["1620000000000000001", "Error: Connection refused"],
                        ["1620000000000000002", "Fatal: Out of memory"]
                    ]
                }
            ]
        }
        
        # Create tool and get error patterns
        tool = LokiQueryTool()
        patterns = tool.get_error_patterns(namespace="test", service="api")
        
        # Verify query
        mock_execute.assert_called_once()
        args, kwargs = mock_execute.call_args
        assert '{namespace="test", service="api"} |~ "(?i)(error|exception|fail|fatal)"' == args[0]
        
        # Verify patterns
        assert "Error" in patterns
        assert "Fatal" in patterns
        assert patterns["Error"]["Connection refused"] == 2
        assert patterns["Fatal"]["Out of memory"] == 1
    
    @patch('common.tools.log_tools.LokiQueryTool.execute')
    def test_get_service_latency(self, mock_execute):
        """Test get_service_latency method"""
        from common.tools.log_tools import LokiQueryTool
        
        # Mock execute response
        mock_execute.return_value = {
            "result": [
                {
                    "stream": {"app": "test-app"},
                    "values": [
                        ["1620000000000000000", "Request completed duration=100"],
                        ["1620000000000000001", "Request completed duration=200"],
                        ["1620000000000000002", "Request completed duration=300"]
                    ]
                }
            ]
        }
        
        # Create tool and get latency stats
        tool = LokiQueryTool()
        stats = tool.get_service_latency(namespace="test", service="api")
        
        # Verify query
        mock_execute.assert_called_once()
        args, kwargs = mock_execute.call_args
        assert '{namespace="test", service="api"} |~ "duration=[0-9]+"' == args[0]
        
        # Verify stats
        assert stats["count"] == 3
        assert stats["min"] == 100
        assert stats["max"] == 300
        assert stats["avg"] == 200
        assert stats["p95"] == 300
        assert stats["p99"] == 300
    
    @patch('common.tools.log_tools.LokiQueryTool.execute')
    def test_get_service_latency_no_data(self, mock_execute):
        """Test get_service_latency method with no data"""
        from common.tools.log_tools import LokiQueryTool
        
        # Mock empty response
        mock_execute.return_value = {"result": []}
        
        # Create tool and get latency stats
        tool = LokiQueryTool()
        stats = tool.get_service_latency(namespace="test", service="api")
        
        # Verify error response when no data
        assert "error" in stats
        assert stats["error"] == "No latency data found"
    
    @patch('common.tools.log_tools.LokiQueryTool.execute')
    @patch('common.tools.log_tools.LokiQueryTool.get_error_patterns')
    def test_get_service_errors(self, mock_get_error_patterns, mock_execute):
        """Test get_service_errors method"""
        from common.tools.log_tools import LokiQueryTool
        
        # Setup mock responses
        mock_execute.side_effect = [
            # First call - total logs
            {
                "result": [
                    {
                        "stream": {"app": "test-app"},
                        "values": [["1", "log1"], ["2", "log2"], ["3", "log3"], ["4", "log4"], ["5", "log5"]]
                    }
                ]
            },
            # Second call - error logs
            {
                "result": [
                    {
                        "stream": {"app": "test-app"},
                        "values": [["1", "Error log"]]
                    }
                ]
            }
        ]
        
        mock_get_error_patterns.return_value = {"Error": {"Connection refused": 1}}
        
        # Create tool and get error stats
        tool = LokiQueryTool()
        stats = tool.get_service_errors(namespace="test", service="api")
        
        # Verify queries
        assert mock_execute.call_count == 2
        calls = [
            call('{namespace="test", service="api"}', None, None, 100),
            call('{namespace="test", service="api"} |~ "(?i)(error|exception|fail|fatal)"', None, None, 100)
        ]
        mock_execute.assert_has_calls(calls)
        
        # Verify stats
        assert stats["total_requests"] == 5
        assert stats["error_count"] == 1
        assert stats["error_rate"] == 0.2
        assert stats["error_patterns"] == {"Error": {"Connection refused": 1}}


class TestPodLogTool:
    def test_name_and_description(self):
        """Test name and description properties"""
        from common.tools.log_tools import PodLogTool
        
        tool = PodLogTool()
        assert tool.name == "pod_logs"
        assert tool.description == "Retrieve logs from Kubernetes pods using kubectl"
    
    @patch('common.tools.log_tools.subprocess.check_output')
    def test_execute_pod_name(self, mock_check_output):
        """Test retrieving logs with pod name"""
        from common.tools.log_tools import PodLogTool
        
        # Mock subprocess output
        mock_check_output.return_value = "Sample log output"
        
        # Create tool and execute
        tool = PodLogTool()
        logs = tool.execute(namespace="test-ns", pod_name="test-pod")
        
        # Verify subprocess call
        mock_check_output.assert_called_once_with(
            ["kubectl", "logs", "test-pod", "-n", "test-ns", "--tail", "100"],
            stderr=-2,  # subprocess.STDOUT
            universal_newlines=True
        )
        
        # Verify result
        assert logs == {"test-pod": "Sample log output"}
    
    @patch('common.tools.log_tools.subprocess.check_output')
    def test_execute_with_selector(self, mock_check_output):
        """Test retrieving logs with selector"""
        from common.tools.log_tools import PodLogTool
        
        # Mock subprocess output
        mock_check_output.return_value = "Sample log output"
        
        # Create tool and execute
        tool = PodLogTool()
        logs = tool.execute(namespace="test-ns", selector="app=test")
        
        # Verify subprocess call
        mock_check_output.assert_called_once_with(
            ["kubectl", "logs", "-l", "app=test", "-n", "test-ns", "--tail", "100"],
            stderr=-2,  # subprocess.STDOUT
            universal_newlines=True
        )
    
    @patch('common.tools.log_tools.subprocess.check_output')
    def test_execute_with_container(self, mock_check_output):
        """Test retrieving logs with container specified"""
        from common.tools.log_tools import PodLogTool
        
        # Mock subprocess output
        mock_check_output.return_value = "Sample log output"
        
        # Create tool and execute
        tool = PodLogTool()
        logs = tool.execute(namespace="test-ns", pod_name="test-pod", container="test-container")
        
        # Verify subprocess call
        mock_check_output.assert_called_once_with(
            ["kubectl", "logs", "test-pod", "-n", "test-ns", "-c", "test-container", "--tail", "100"],
            stderr=-2,  # subprocess.STDOUT
            universal_newlines=True
        )
    
    @patch('common.tools.log_tools.subprocess.check_output')
    def test_execute_with_previous(self, mock_check_output):
        """Test retrieving logs from previous container"""
        from common.tools.log_tools import PodLogTool
        
        # Mock subprocess output
        mock_check_output.return_value = "Sample log output"
        
        # Create tool and execute
        tool = PodLogTool()
        logs = tool.execute(namespace="test-ns", pod_name="test-pod", previous=True)
        
        # Verify subprocess call
        mock_check_output.assert_called_once_with(
            ["kubectl", "logs", "test-pod", "-n", "test-ns", "--tail", "100", "-p"],
            stderr=-2,  # subprocess.STDOUT
            universal_newlines=True
        )
    
    @patch('common.tools.log_tools.subprocess.check_output')
    def test_execute_with_since(self, mock_check_output):
        """Test retrieving logs since specific time"""
        from common.tools.log_tools import PodLogTool
        
        # Mock subprocess output
        mock_check_output.return_value = "Sample log output"
        
        # Create tool and execute
        tool = PodLogTool()
        logs = tool.execute(namespace="test-ns", pod_name="test-pod", since="1h")
        
        # Verify subprocess call
        mock_check_output.assert_called_once_with(
            ["kubectl", "logs", "test-pod", "-n", "test-ns", "--tail", "100", "--since", "1h"],
            stderr=-2,  # subprocess.STDOUT
            universal_newlines=True
        )
    
    def test_execute_missing_params(self):
        """Test error when pod_name and selector are both missing"""
        from common.tools.log_tools import PodLogTool
        
        tool = PodLogTool()
        with pytest.raises(ValueError) as excinfo:
            tool.execute(namespace="test-ns")
        
        assert "Either pod_name or selector must be provided" in str(excinfo.value)