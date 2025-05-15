import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from common.tools.tempo_tools import TempoTraceTool, TempoServiceTool

@pytest.fixture
def tempo_trace_tool():
    """Fixture to create a TempoTraceTool instance for testing"""
    return TempoTraceTool(tempo_url="http://tempo-test:3100")

@pytest.fixture
def tempo_service_tool():
    """Fixture to create a TempoServiceTool instance for testing"""
    return TempoServiceTool(tempo_url="http://tempo-test:3100")

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

class TestTempoTraceTool:
    """Tests for the TempoTraceTool class"""

    def test_initialization_with_url(self):
        """Test TempoTraceTool initialization with a provided URL"""
        tool = TempoTraceTool(tempo_url="http://custom-tempo:3100")
        assert tool.tempo_url == "http://custom-tempo:3100"
        
    def test_initialization_without_url(self):
        """Test TempoTraceTool initialization without a URL (should use default)"""
        with patch.dict('os.environ', {}, clear=True):
            tool = TempoTraceTool()
            assert tool.tempo_url == "http://tempo:3100"
            
    def test_name_and_description(self, tempo_trace_tool):
        """Test the name and description properties"""
        assert tempo_trace_tool.name == "tempo_traces"
        assert "Query traces from Tempo" in tempo_trace_tool.description
        
    @patch('requests.get')
    def test_execute_basic_query(self, mock_get, tempo_trace_tool, sample_trace_response):
        """Test basic query execution"""
        # Setup the mock
        mock_response = MagicMock()
        mock_response.json.return_value = sample_trace_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Execute the tool
        result = tempo_trace_tool.execute(service="frontend")
        
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
    def test_execute_with_filters(self, mock_get, tempo_trace_tool, sample_trace_response):
        """Test query execution with multiple filters"""
        # Setup the mock
        mock_response = MagicMock()
        mock_response.json.return_value = sample_trace_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Execute the tool with filters
        result = tempo_trace_tool.execute(
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
    def test_execute_with_time_range(self, mock_get, tempo_trace_tool, sample_trace_response):
        """Test query execution with custom time range"""
        # Setup the mock
        mock_response = MagicMock()
        mock_response.json.return_value = sample_trace_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Execute the tool with custom time range
        start_time = "2023-05-01T00:00:00Z"
        end_time = "2023-05-02T00:00:00Z"
        result = tempo_trace_tool.execute(
            service="frontend",
            start=start_time,
            end=end_time
        )
        
        # Verify time range parameters
        args, kwargs = mock_get.call_args
        assert kwargs["params"]["start"] == start_time
        assert kwargs["params"]["end"] == end_time
        
    @patch('requests.get')
    def test_execute_request_exception(self, mock_get, tempo_trace_tool):
        """Test handling of request exceptions"""
        # Setup the mock to raise an exception
        mock_get.side_effect = Exception("Connection error")
        
        # Execute the tool
        result = tempo_trace_tool.execute(service="frontend")
        
        # Verify error handling
        assert "error" in result
        assert "Connection error" in result["error"]
        
    @patch('requests.get')
    def test_get_trace_by_id(self, mock_get, tempo_trace_tool, sample_trace_detail_response):
        """Test retrieving a trace by ID"""
        # Setup the mock
        mock_response = MagicMock()
        mock_response.json.return_value = sample_trace_detail_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Execute the tool
        result = tempo_trace_tool.get_trace_by_id("1234567890abcdef")
        
        # Verify the URL
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "http://tempo-test:3100/api/traces/1234567890abcdef"
        
        # Verify the result
        assert result["trace_id"] == "1234567890abcdef"
        assert "spans" in result
        assert len(result["spans"]) == 2
        assert "frontend" in result["services"]
        assert len(result["issues"]) == 0
        
    @patch('requests.get')
    def test_get_trace_by_id_with_long_span(self, mock_get, tempo_trace_tool, sample_trace_detail_response):
        """Test identifying long spans as issues"""
        # Modify the response to include a long-running span
        long_span = {
            "spanId": "span3",
            "parentSpanId": "span1",
            "name": "slow operation",
            "startTimeUnixNano": "1620000000050000000",
            "endTimeUnixNano": "1620000001550000000",  # 1.5 seconds
            "attributes": []
        }
        sample_trace_detail_response["batches"][0]["spans"].append(long_span)
        
        # Setup the mock
        mock_response = MagicMock()
        mock_response.json.return_value = sample_trace_detail_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Execute the tool
        result = tempo_trace_tool.get_trace_by_id("1234567890abcdef")
        
        # Verify long span is identified as an issue
        assert len(result["issues"]) >= 1
        assert any(issue["type"] == "long_duration" and issue["span_id"] == "span3" for issue in result["issues"])

class TestTempoServiceTool:
    """Tests for the TempoServiceTool class"""

    def test_initialization(self):
        """Test TempoServiceTool initialization"""
        tool = TempoServiceTool(tempo_url="http://custom-tempo:3100")
        assert tool.tempo_url == "http://custom-tempo:3100"
        
    def test_name_and_description(self, tempo_service_tool):
        """Test the name and description properties"""
        assert tempo_service_tool.name == "tempo_service_analysis"
        assert "Analyze service performance" in tempo_service_tool.description
        
    @patch('common.tools.tempo_tools.TempoTraceTool.execute')
    def test_execute_basic_analysis(self, mock_execute, tempo_service_tool):
        """Test basic service analysis"""
        # This test will need to be expanded once we implement the execute method for TempoServiceTool
        mock_execute.return_value = {"traces": []}
        
        # Execute the tool
        result = tempo_service_tool.execute(service="frontend")
        
        # Verify TempoTraceTool.execute was called
        mock_execute.assert_called_once()
        args, kwargs = mock_execute.call_args
        assert kwargs["service"] == "frontend"