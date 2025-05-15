import pytest
import json
from unittest.mock import Mock, patch
from agents.tracing_agent.agent import TracingAgent

@pytest.fixture
def tracing_agent():
    with patch('nats.connect') as mock_connect:
        mock_js = Mock()
        mock_connect.return_value.jetstream.return_value = mock_js
        agent = TracingAgent(jaeger_url="http://test-jaeger:16686", tempo_url="http://test-tempo:3200")
        agent.js = mock_js
        return agent

def test_tracing_agent_initialization(tracing_agent):
    assert tracing_agent.jaeger_url == "http://test-jaeger:16686"
    assert tracing_agent.tempo_url == "http://test-tempo:3200"
    assert len(tracing_agent.crewai_tools) == 5  # All tools should be crewai tools now
    assert all(tool.name in ["trace_query", "trace_analysis", "tempo_query", "tempo_search", "tempo_performance"] 
              for tool in tracing_agent.crewai_tools)

@pytest.mark.asyncio
async def test_tracing_agent_connect(tracing_agent):
    await tracing_agent.connect()
    assert tracing_agent.js is not None

@pytest.mark.asyncio
async def test_tracing_agent_message_handler(tracing_agent):
    # Mock message
    mock_msg = Mock()
    mock_msg.data = json.dumps({
        "alert_id": "test-alert",
        "labels": {
            "alertname": "HighLatency",
            "service": "test-service"
        }
    }).encode()
    
    # Mock crew.kickoff() result
    mock_result = "Test analysis result"
    
    with patch('crewai.Crew.kickoff', return_value=mock_result):
        await tracing_agent.message_handler(mock_msg)
        
        # Verify that the result was published
        tracing_agent.js.publish.assert_called_once()
        published_data = json.loads(tracing_agent.js.publish.call_args[0][1].decode())
        assert published_data["agent"] == "tracing"
        assert published_data["alert_id"] == "test-alert"
        assert published_data["analysis"] == mock_result

@pytest.mark.asyncio
async def test_tracing_agent_listen(tracing_agent):
    with patch('asyncio.sleep') as mock_sleep:
        # Make sleep return immediately for testing
        mock_sleep.side_effect = Exception("Test exit")
        
        try:
            await tracing_agent.listen()
        except Exception as e:
            assert str(e) == "Test exit"
        
        # Verify subscription
        tracing_agent.js.subscribe.assert_called_once()
        assert tracing_agent.js.subscribe.call_args[0][0] == "tracing_agent" 