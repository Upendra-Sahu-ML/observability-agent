import os
import pytest
from unittest.mock import Mock, patch
from common.tools.notification_tools import (
    SlackNotificationTool,
    PagerDutyNotificationTool,
    WebexNotificationTool
)

@pytest.fixture
def mock_slack_client():
    with patch('slack_sdk.WebClient') as mock:
        yield mock

@pytest.fixture
def mock_pagerduty_client():
    with patch('pagerduty_sdk.PagerDutyClient') as mock:
        yield mock

@pytest.fixture
def mock_webex_client():
    with patch('webexteamssdk.WebexTeamsAPI') as mock:
        yield mock

class TestSlackNotificationTool:
    def test_init(self, mock_slack_client):
        os.environ['SLACK_BOT_TOKEN'] = 'test-token'
        os.environ['SLACK_DEFAULT_CHANNEL'] = '#test-channel'
        
        tool = SlackNotificationTool()
        assert tool.client == mock_slack_client.return_value
        assert tool.default_channel == '#test-channel'
    
    def test_execute_success(self, mock_slack_client):
        tool = SlackNotificationTool()
        mock_response = {'ok': True, 'channel': 'test-channel'}
        mock_slack_client.return_value.chat_postMessage.return_value = mock_response
        
        result = tool.execute("Test message")
        assert result['status'] == 'success'
        assert result['response'] == mock_response
    
    def test_execute_error(self, mock_slack_client):
        tool = SlackNotificationTool()
        mock_slack_client.return_value.chat_postMessage.side_effect = Exception("API Error")
        
        result = tool.execute("Test message")
        assert result['status'] == 'error'
        assert 'API Error' in result['error']

class TestPagerDutyNotificationTool:
    def test_init(self, mock_pagerduty_client):
        os.environ['PAGERDUTY_API_TOKEN'] = 'test-token'
        
        tool = PagerDutyNotificationTool()
        assert tool.client == mock_pagerduty_client.return_value
    
    def test_execute_success(self, mock_pagerduty_client):
        tool = PagerDutyNotificationTool()
        mock_response = {'id': 'test-incident'}
        mock_pagerduty_client.return_value.incidents.create.return_value = mock_response
        
        result = tool.execute("Test incident", "Test description")
        assert result['status'] == 'success'
        assert result['response'] == mock_response
    
    def test_execute_error(self, mock_pagerduty_client):
        tool = PagerDutyNotificationTool()
        mock_pagerduty_client.return_value.incidents.create.side_effect = Exception("API Error")
        
        result = tool.execute("Test incident", "Test description")
        assert result['status'] == 'error'
        assert 'API Error' in result['error']

class TestWebexNotificationTool:
    def test_init(self, mock_webex_client):
        os.environ['WEBEX_ACCESS_TOKEN'] = 'test-token'
        os.environ['WEBEX_DEFAULT_ROOM_ID'] = 'test-room'
        
        tool = WebexNotificationTool()
        assert tool.client == mock_webex_client.return_value
        assert tool.default_room_id == 'test-room'
    
    def test_execute_success(self, mock_webex_client):
        tool = WebexNotificationTool()
        mock_response = {'id': 'test-message'}
        mock_webex_client.return_value.messages.create.return_value = mock_response
        
        result = tool.execute("Test message")
        assert result['status'] == 'success'
        assert result['response'] == mock_response
    
    def test_execute_error(self, mock_webex_client):
        tool = WebexNotificationTool()
        mock_webex_client.return_value.messages.create.side_effect = Exception("API Error")
        
        result = tool.execute("Test message")
        assert result['status'] == 'error'
        assert 'API Error' in result['error'] 