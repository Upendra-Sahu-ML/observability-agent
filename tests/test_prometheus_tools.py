import os
import pytest
import json
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta

from common.tools.prometheus_tools import PrometheusTools

class TestPrometheusTools:
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        # Create proper patch for requests.get to prevent actual HTTP requests
        patcher = patch('requests.get')
        self.mock_get = patcher.start()
        
        # Set up mock response
        self.mock_response = MagicMock()
        self.mock_response.status_code = 200
        self.mock_response.json.return_value = {
            'status': 'success',
            'data': {
                'resultType': 'vector',
                'result': [
                    {
                        'metric': {'__name__': 'up', 'job': 'prometheus', 'instance': 'localhost:9090'},
                        'value': [1619712424.744, '1']
                    }
                ]
            }
        }
        self.mock_get.return_value = self.mock_response
        
        # Environment variables
        os.environ['PROMETHEUS_URL'] = 'http://test-prometheus:9090'
        
        yield
        
        # Stop the patcher after the test
        patcher.stop()
    
    def test_init(self):
        """Test initialization of PrometheusTools"""
        tool = PrometheusTools()
        assert tool.prometheus_url == 'http://test-prometheus:9090'
        assert tool.api_path == '/api/v1/'
    
    def test_init_custom_url(self):
        """Test initialization with custom URL"""
        tool = PrometheusTools(prometheus_url='http://custom-prometheus:9090')
        assert tool.prometheus_url == 'http://custom-prometheus:9090'
    
    def test_query(self):
        """Test executing a simple query"""
        tool = PrometheusTools()
        result = tool.query('up')
        
        # Verify result
        assert result['status'] == 'success'
        assert 'data' in result
        assert result['data']['result'][0]['metric']['__name__'] == 'up'
        
        # Verify request
        self.mock_get.assert_called_once()
        args, kwargs = self.mock_get.call_args
        assert 'http://test-prometheus:9090/api/v1/query' in args[0]
        assert 'query=up' in kwargs['params']
    
    def test_query_with_time(self):
        """Test executing a query with a specific time"""
        tool = PrometheusTools()
        result = tool.query('up', time='2023-05-13T12:00:00Z')
        
        # Verify result
        assert result['status'] == 'success'
        
        # Verify request
        self.mock_get.assert_called_once()
        args, kwargs = self.mock_get.call_args
        assert 'time' in kwargs['params']
        assert kwargs['params']['time'] == '2023-05-13T12:00:00Z'
    
    def test_query_error_response(self):
        """Test handling error response from Prometheus"""
        # Configure mock to return an error
        self.mock_response.status_code = 400
        self.mock_response.text = "Bad request"
        
        tool = PrometheusTools()
        result = tool.query('invalid{')
        
        # Verify result
        assert result['status'] == 'error'
        assert 'error' in result
        assert 'Query failed with status 400' in result['error']
    
    def test_range_query(self):
        """Test executing a range query"""
        # Set up mock response for range query
        self.mock_response.json.return_value = {
            'status': 'success',
            'data': {
                'resultType': 'matrix',
                'result': [
                    {
                        'metric': {'__name__': 'up', 'job': 'prometheus'},
                        'values': [
                            [1619712424.744, '1'],
                            [1619712484.744, '1'],
                            [1619712544.744, '1']
                        ]
                    }
                ]
            }
        }
        
        tool = PrometheusTools()
        end = datetime.now().isoformat() + 'Z'
        start = (datetime.now() - timedelta(hours=1)).isoformat() + 'Z'
        
        result = tool.range_query(
            'up',
            start=start,
            end=end,
            step='15s'
        )
        
        # Verify result
        assert result['status'] == 'success'
        assert 'data' in result
        assert len(result['data']['result'][0]['values']) == 3
        
        # Verify request
        self.mock_get.assert_called_once()
        args, kwargs = self.mock_get.call_args
        assert 'http://test-prometheus:9090/api/v1/query_range' in args[0]
        assert kwargs['params']['query'] == 'up'
        assert kwargs['params']['start'] == start
        assert kwargs['params']['end'] == end
        assert kwargs['params']['step'] == '15s'
    
    def test_get_service_health(self):
        """Test get_service_health method"""
        # Configure mock to return health data
        self.mock_response.json.return_value = {
            'status': 'success',
            'data': {
                'resultType': 'vector',
                'result': [
                    {
                        'metric': {'service': 'api'},
                        'value': [1619712424.744, '1']
                    }
                ]
            }
        }
        
        tool = PrometheusTools()
        result = tool.get_service_health('api')
        
        # Verify result
        assert result['status'] == 'success'
        assert result['health'] == 'healthy'
        
        # Verify query
        self.mock_get.assert_called_once()
        args, kwargs = self.mock_get.call_args
        assert 'query' in kwargs['params']
        assert 'up{service="api"}' == kwargs['params']['query']
    
    def test_get_resource_usage(self):
        """Test get_resource_usage method"""
        # Configure mock to return resource usage data
        self.mock_response.json.return_value = {
            'status': 'success',
            'data': {
                'resultType': 'vector',
                'result': [
                    {
                        'metric': {'service': 'api'},
                        'value': [1619712424.744, '0.75']
                    }
                ]
            }
        }
        
        tool = PrometheusTools()
        result = tool.get_resource_usage('api', 'cpu')
        
        # Verify result
        assert result['status'] == 'success'
        assert 'usage' in result
        assert result['usage'] == 0.75
        
        # Verify correct query was made
        self.mock_get.assert_called_once()
        args, kwargs = self.mock_get.call_args
        assert 'query' in kwargs['params']
        
    def test_get_resource_usage_unsupported(self):
        """Test get_resource_usage with unsupported resource type"""
        tool = PrometheusTools()
        result = tool.get_resource_usage('api', 'unsupported')
        
        # Verify result contains error
        assert result['status'] == 'error'
        assert 'error' in result
        assert 'Unsupported resource type' in result['error']
        
        # Verify no query was made
        self.mock_get.assert_not_called()
    
    def test_get_service_dependencies(self):
        """Test get_service_dependencies method"""
        # Configure mock to return dependency data
        self.mock_response.json.return_value = {
            'status': 'success',
            'data': {
                'resultType': 'vector',
                'result': [
                    {
                        'metric': {'source_service': 'api', 'destination_service': 'database'},
                        'value': [1619712424.744, '100']
                    },
                    {
                        'metric': {'source_service': 'api', 'destination_service': 'cache'},
                        'value': [1619712424.744, '50']
                    }
                ]
            }
        }
        
        tool = PrometheusTools()
        result = tool.get_service_dependencies('api')
        
        # Verify result
        assert result['status'] == 'success'
        assert 'dependencies' in result
        assert len(result['dependencies']) == 2
        assert 'database' in [dep['service'] for dep in result['dependencies']]
        
        # Verify correct query was made
        self.mock_get.assert_called_once()
        args, kwargs = self.mock_get.call_args
        assert 'query' in kwargs['params']
    
    def test_list_metrics(self):
        """Test list_metrics method"""
        # Configure mock to return metrics data
        self.mock_response.json.return_value = {
            'status': 'success',
            'data': ['up', 'http_requests_total', 'process_cpu_seconds_total']
        }
        
        tool = PrometheusTools()
        result = tool.list_metrics()
        
        # Verify result
        assert result['status'] == 'success'
        assert 'metrics' in result
        assert len(result['metrics']) == 3
        assert 'up' in result['metrics']
        
        # Verify endpoint
        self.mock_get.assert_called_once()
        args, kwargs = self.mock_get.call_args
        assert 'http://test-prometheus:9090/api/v1/label/__name__/values' in args[0]
    
    def test_get_metric_metadata(self):
        """Test get_metric_metadata method"""
        # Configure mock to return metadata
        self.mock_response.json.return_value = {
            'status': 'success',
            'data': {
                'up': [
                    {
                        'type': 'gauge',
                        'help': 'Up metric help text',
                        'unit': ''
                    }
                ]
            }
        }
        
        tool = PrometheusTools()
        result = tool.get_metric_metadata('up')
        
        # Verify result
        assert result['status'] == 'success'
        assert 'metadata' in result
        assert 'up' in result['metadata']
        
        # Verify params
        self.mock_get.assert_called_once()
        args, kwargs = self.mock_get.call_args
        assert 'metric' in kwargs['params']
        assert kwargs['params']['metric'] == 'up'
    
    def test_list_targets(self):
        """Test list_targets method"""
        # Configure mock to return targets data
        self.mock_response.json.return_value = {
            'status': 'success',
            'data': {
                'activeTargets': [
                    {
                        'labels': {'job': 'prometheus', 'instance': 'localhost:9090'},
                        'health': 'up'
                    },
                    {
                        'labels': {'job': 'node', 'instance': 'localhost:9100'},
                        'health': 'up'
                    }
                ],
                'droppedTargets': []
            }
        }
        
        tool = PrometheusTools()
        result = tool.list_targets()
        
        # Verify result
        assert result['status'] == 'success'
        assert 'targets' in result
        
        # Verify endpoint
        self.mock_get.assert_called_once()
        args, kwargs = self.mock_get.call_args
        assert 'http://test-prometheus:9090/api/v1/targets' in args[0]
    
    def test_list_targets_with_state(self):
        """Test list_targets with state parameter"""
        tool = PrometheusTools()
        result = tool.list_targets(state='active')
        
        # Verify params
        self.mock_get.assert_called_once()
        args, kwargs = self.mock_get.call_args
        assert 'state' in kwargs['params']
        assert kwargs['params']['state'] == 'active'
    
    def test_get_target_health(self):
        """Test get_target_health method"""
        # Configure mock to return targets data for list_targets
        self.mock_response.json.return_value = {
            'status': 'success',
            'data': {
                'activeTargets': [
                    {
                        'labels': {'job': 'prometheus', 'instance': 'localhost:9090'},
                        'health': 'up'
                    },
                    {
                        'labels': {'job': 'node', 'instance': 'localhost:9100'},
                        'health': 'down'
                    },
                    {
                        'labels': {'job': 'node', 'instance': 'localhost:9101'},
                        'health': 'up'
                    }
                ],
                'droppedTargets': []
            }
        }
        
        tool = PrometheusTools()
        result = tool.get_target_health('node')
        
        # Verify result
        assert result['status'] == 'success'
        assert result['job'] == 'node'
        assert result['healthy_targets'] == 1
        assert result['total_targets'] == 2
        assert result['health_percentage'] == 50.0
        
        # Verify list_targets was called
        self.mock_get.assert_called_once()
        args, kwargs = self.mock_get.call_args
        assert 'http://test-prometheus:9090/api/v1/targets' in args[0]