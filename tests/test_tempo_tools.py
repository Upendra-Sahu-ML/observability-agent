import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import requests

from common.tools.tempo_tools import TempoTools

@pytest.fixture
def tempo_tool():
    """Fixture to create a TempoTools instance for testing"""
    return TempoTools(tempo_url="http://tempo-test:3100")

@pytest.fixture
def tempo_trace_tool():
    """Fixture to maintain backward compatibility with existing tests"""
    return TempoTools(tempo_url="http://tempo-test:3100")

@pytest.fixture
def tempo_service_tool():
    """Fixture to maintain backward compatibility with existing tests"""
    return TempoTools(tempo_url="http://tempo-test:3100")

@pytest.fixture
def sample_trace_response():
    """Sample response data for a trace query"""
    return {
        "traces": [
            {
                "traceID": "1234567890abcdef",
                "rootServiceName": "frontend",
                "rootTraceName": "GET /api/products",
                "durationMs": 235.45,
                "startTimeUnixNano": 1620000000000000000
            },
            {
                "traceID": "abcdef1234567890",
                "rootServiceName": "frontend",
                "rootTraceName": "GET /api/cart",
                "durationMs": 145.32,
                "startTimeUnixNano": 1620000100000000000
            }
        ]
    }

@pytest.fixture
def sample_trace_detail_response():
    """Sample response data for a trace detail query"""
    return {
        "batches": [
            {
                "resource": {
                    "attributes": [
                        {
                            "key": "service.name",
                            "value": {"stringValue": "frontend"}
                        }
                    ]
                },
                "spans": [
                    {
                        "spanId": "span1",
                        "parentSpanId": "",
                        "name": "GET /api/products",
                        "kind": "SERVER",
                        "startTimeUnixNano": "1620000000000000000",
                        "endTimeUnixNano": "1620000000235450000",
                        "attributes": [
                            {
                                "key": "http.method",
                                "value": {"stringValue": "GET"}
                            },
                            {
                                "key": "http.url",
                                "value": {"stringValue": "/api/products"}
                            }
                        ],
                        "events": []
                    },
                    {
                        "spanId": "span2",
                        "parentSpanId": "span1",
                        "name": "database query",
                        "kind": "CLIENT",
                        "startTimeUnixNano": "1620000000050000000",
                        "endTimeUnixNano": "1620000000150000000",
                        "attributes": [
                            {
                                "key": "db.system",
                                "value": {"stringValue": "postgresql"}
                            },
                            {
                                "key": "db.statement",
                                "value": {"stringValue": "SELECT * FROM products"}
                            }
                        ],
                        "events": []
                    }
                ]
            }
        ]
    }

class TestTempoTools:
    """Tests for the TempoTools class"""

    def test_initialization_with_url(self):
        """Test TempoTools initialization with a provided URL"""
        tool = TempoTools(tempo_url="http://custom-tempo:3100")
        assert tool.tempo_url == "http://custom-tempo:3100"
        
    def test_initialization_without_url(self):
        """Test TempoTools initialization without a URL (should use default)"""
        with patch.dict('os.environ', {}, clear=True):
            tool = TempoTools()
            assert tool.tempo_url == "http://tempo:3100"
            
    @patch('requests.get')
    def test_query_traces(self, mock_get, tempo_tool, sample_trace_response):
        """Test basic query execution"""
        # Setup the mock
        mock_response = MagicMock()
        mock_response.json.return_value = sample_trace_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Execute the tool
        result = tempo_tool.query_traces(service="frontend")
        
        # Verify the URL and parameters
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "http://tempo-test:3100/api/search"
        assert "service" in kwargs["params"]
        assert kwargs["params"]["service"] == "frontend"
        
        # Verify the result
        assert "traces" in result
        assert len(result["traces"]) == 2
        assert result["trace_count"] == 2
        assert "statistics" in result
        assert result["traces"][0]["trace_id"] == "1234567890abcdef"
        assert result["traces"][0]["root_service"] == "frontend"
        
    @patch('requests.get')
    def test_query_traces_with_filters(self, mock_get, tempo_tool, sample_trace_response):
        """Test query execution with multiple filters"""
        # Setup the mock
        mock_response = MagicMock()
        mock_response.json.return_value = sample_trace_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Execute the tool with filters
        result = tempo_tool.query_traces(
            service="frontend",
            operation="GET /api/products",
            tags={"http.method": "GET", "status.code": "200"},
            minDuration="100ms",
            maxDuration="500ms",
            limit=10
        )
        
        # Verify parameters were correctly set
        args, kwargs = mock_get.call_args
        assert kwargs["params"]["service"] == "frontend"
        assert kwargs["params"]["operation"] == "GET /api/products"
        assert kwargs["params"]["tag.http.method"] == "GET"
        assert kwargs["params"]["tag.status.code"] == "200"
        assert kwargs["params"]["minDuration"] == "100ms"
        assert kwargs["params"]["maxDuration"] == "500ms"
        assert kwargs["params"]["limit"] == "10"
        
    @patch('requests.get')
    def test_query_traces_with_time_range(self, mock_get, tempo_tool, sample_trace_response):
        """Test query execution with custom time range"""
        # Setup the mock
        mock_response = MagicMock()
        mock_response.json.return_value = sample_trace_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Execute the tool with custom time range
        start_time = "2023-05-01T00:00:00Z"
        end_time = "2023-05-02T00:00:00Z"
        result = tempo_tool.query_traces(
            service="frontend",
            start=start_time,
            end=end_time
        )
        
        # Verify time range parameters
        args, kwargs = mock_get.call_args
        assert kwargs["params"]["start"] == start_time
        assert kwargs["params"]["end"] == end_time
        
    @patch('requests.get')
    def test_query_traces_request_exception(self, mock_get, tempo_tool):
        """Test handling of request exceptions"""
        # Setup the mock to raise an exception
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        
        # Execute the tool
        result = tempo_tool.query_traces(service="frontend")
        
        # Verify error handling
        assert "error" in result
        assert "Connection error" in result["error"]
        
    @patch('requests.get')
    def test_get_trace_by_id(self, mock_get, tempo_tool, sample_trace_detail_response):
        """Test retrieving a trace by ID"""
        # Setup the mock
        mock_response = MagicMock()
        mock_response.json.return_value = sample_trace_detail_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Execute the tool
        result = tempo_tool.get_trace_by_id("1234567890abcdef")
        
        # Verify the URL
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "http://tempo-test:3100/api/traces/1234567890abcdef"
        
        # Verify the result
        assert result["trace_id"] == "1234567890abcdef"
        assert "spans" in result
        assert len(result["spans"]) == 2
        assert "frontend" in result["services"]
        
    @patch('requests.get')
    def test_analyze_service_performance(self, mock_get, tempo_tool):
        """Test service performance analysis"""
        # This test will need to be expanded with proper mocking of the dependent methods
        with patch.object(TempoTools, 'query_traces') as mock_query_traces, \
             patch.object(TempoTools, 'get_error_analysis') as mock_error_analysis, \
             patch.object(TempoTools, 'get_service_latency_analysis') as mock_latency_analysis, \
             patch.object(TempoTools, 'get_service_dependencies') as mock_dependencies:
            
            # Setup the mocks
            mock_query_traces.return_value = {
                "trace_count": 100,
                "statistics": {
                    "avg_duration_ms": 150,
                    "p95_duration_ms": 300,
                    "max_duration_ms": 500
                }
            }
            mock_error_analysis.return_value = {
                "total_error_traces": 5,
                "error_rate": 0.05,
                "error_messages": {"Connection timeout": 3, "Database error": 2}
            }
            mock_latency_analysis.return_value = {
                "operations": {
                    "GET /api/products": {
                        "count": 50,
                        "avg": 120,
                        "p95": 250,
                        "max": 400
                    },
                    "GET /api/cart": {
                        "count": 30,
                        "avg": 180,
                        "p95": 350,
                        "max": 500
                    }
                }
            }
            mock_dependencies.return_value = {
                "downstream": {
                    "database": {"count": 80, "errors": 2},
                    "cache": {"count": 50, "errors": 0}
                },
                "upstream": {
                    "gateway": {"count": 100, "errors": 0}
                }
            }
            
            # Execute the method
            result = tempo_tool.analyze_service_performance("frontend")
            
            # Verify the result
            assert result["service"] == "frontend"
            assert result["trace_count"] == 100
            assert result["avg_duration_ms"] == 150
            assert result["p95_duration_ms"] == 300
            assert result["max_duration_ms"] == 500
            assert result["error_count"] == 5
            assert result["error_rate"] == 0.05
            assert "operations" in result
            assert "dependencies" in result
            assert "issues" in result