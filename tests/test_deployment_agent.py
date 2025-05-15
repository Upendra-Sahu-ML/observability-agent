import pytest
import json
from unittest.mock import Mock, patch
from agents.deployment_agent.deploy import DeploymentAgent

@pytest.fixture
def deployment_agent():
    with patch('nats.connect') as mock_connect:
        mock_js = Mock()
        mock_connect.return_value.jetstream.return_value = mock_js
        agent = DeploymentAgent(
            argocd_server="https://test-argocd:443",
            git_repo_path="/test/repo"
        )
        agent.js = mock_js
        return agent

def test_deployment_agent_initialization(deployment_agent):
    assert deployment_agent.argocd_server == "https://test-argocd:443"
    assert deployment_agent.git_repo_path == "/test/repo"
    assert len(deployment_agent.crewai_tools) == 5  # All tools should be crewai tools now
    assert all(tool.name in ["git_changes", "argocd_status", "kube_deployment", "deployment_status", "rollback"] 
              for tool in deployment_agent.crewai_tools)

@pytest.mark.asyncio
async def test_deployment_agent_connect(deployment_agent):
    await deployment_agent.connect()
    assert deployment_agent.js is not None

@pytest.mark.asyncio
async def test_deployment_agent_message_handler(deployment_agent):
    # Mock message
    mock_msg = Mock()
    mock_msg.data = json.dumps({
        "alert_id": "test-alert",
        "labels": {
            "alertname": "DeploymentFailed",
            "service": "test-service",
            "namespace": "test-namespace"
        }
    }).encode()
    
    # Mock crew.kickoff() result
    mock_result = "Test analysis result"
    
    with patch('crewai.Crew.kickoff', return_value=mock_result):
        await deployment_agent.message_handler(mock_msg)
        
        # Verify that the result was published
        deployment_agent.js.publish.assert_called_once()
        published_data = json.loads(deployment_agent.js.publish.call_args[0][1].decode())
        assert published_data["agent"] == "deployment"
        assert published_data["alert_id"] == "test-alert"
        assert published_data["analysis"] == mock_result

@pytest.mark.asyncio
async def test_deployment_agent_listen(deployment_agent):
    with patch('asyncio.sleep') as mock_sleep:
        # Make sleep return immediately for testing
        mock_sleep.side_effect = Exception("Test exit")
        
        try:
            await deployment_agent.listen()
        except Exception as e:
            assert str(e) == "Test exit"
        
        # Verify subscription
        deployment_agent.js.subscribe.assert_called_once()
        assert deployment_agent.js.subscribe.call_args[0][0] == "deployment_agent" 