import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from common.tools.notification_tools import NotificationTools

class TestNotificationTools:
    @pytest.fixture
    def env_setup(self):
        """Setup environment variables for tests"""
        old_env = os.environ.copy()
        os.environ.update({
            'SLACK_BOT_TOKEN': 'test-slack-token',
            'SLACK_DEFAULT_CHANNEL': '#test-channel',
            'PAGERDUTY_API_TOKEN': 'test-pd-token',
            'PAGERDUTY_SERVICE_ID': 'test-service-id',
            'WEBEX_ACCESS_TOKEN': 'test-webex-token',
            'WEBEX_DEFAULT_ROOM_ID': 'test-room-id'
        })
        yield
        os.environ.clear()
        os.environ.update(old_env)

    @pytest.fixture
    def mock_clients(self):
        """Create mock clients for notification services"""
        with patch('common.tools.notification_tools.WebClient') as mock_slack_client, \
             patch('common.tools.notification_tools.PagerDutyClient') as mock_pd_client, \
             patch('common.tools.notification_tools.WebexTeamsAPI') as mock_webex_client:
            
            # Configure the mock Slack client
            mock_slack_instance = MagicMock()
            mock_slack_client.return_value = mock_slack_instance
            mock_slack_instance.chat_postMessage.return_value = {'ok': True, 'ts': '1234', 'channel': 'C1234'}
            
            # Configure the mock PagerDuty client
            mock_pd_instance = MagicMock()
            mock_pd_client.return_value = mock_pd_instance
            mock_pd_instance.create_incident.return_value = {'id': 'PD1234', 'html_url': 'https://pagerduty.com/incidents/PD1234'}
            
            # Configure the mock Webex client
            mock_webex_instance = MagicMock()
            mock_webex_client.return_value = mock_webex_instance
            mock_webex_instance.messages.create.return_value = {'id': 'WX1234'}
            
            yield {
                'slack': mock_slack_instance,
                'pagerduty': mock_pd_instance,
                'webex': mock_webex_instance
            }
    
    def test_init(self, env_setup, mock_clients):
        """Test initialization of NotificationTools"""
        tool = NotificationTools()
        
        # Check Slack initialization
        assert tool.slack_token == 'test-slack-token'
        assert tool.slack_default_channel == '#test-channel'
        assert tool.slack_client is not None
        
        # Check PagerDuty initialization
        assert tool.pagerduty_token == 'test-pd-token'
        assert tool.pagerduty_service_id == 'test-service-id'
        assert tool.pagerduty_client is not None
        
        # Check Webex initialization
        assert tool.webex_token == 'test-webex-token'
        assert tool.webex_default_room_id == 'test-room-id'
        assert tool.webex_client is not None
    
    def test_send_slack_message(self, env_setup, mock_clients):
        """Test sending a message to Slack"""
        tool = NotificationTools()
        result = tool.send_slack_message(message='Test message')
        
        # Verify result
        assert result['status'] == 'success'
        
        # Verify the message was sent with correct parameters
        mock_clients['slack'].chat_postMessage.assert_called_once()
        call_args = mock_clients['slack'].chat_postMessage.call_args
        assert call_args.kwargs['channel'] == '#test-channel'
        assert call_args.kwargs['text'] == 'Test message'
        assert call_args.kwargs['blocks'] is not None
    
    def test_send_slack_message_custom_channel(self, env_setup, mock_clients):
        """Test sending a message to Slack with custom channel"""
        tool = NotificationTools()
        result = tool.send_slack_message(message='Test message', channel='#custom-channel')
        
        # Verify the message was sent to the custom channel
        call_args = mock_clients['slack'].chat_postMessage.call_args
        assert call_args.kwargs['channel'] == '#custom-channel'
    
    def test_send_slack_message_error(self, env_setup, mock_clients):
        """Test error handling when sending Slack message"""
        from slack_sdk.errors import SlackApiError
        
        # Configure the Slack client to raise an exception
        mock_clients['slack'].chat_postMessage.side_effect = SlackApiError("Error sending message", {"error": "channel_not_found"})
        
        tool = NotificationTools()
        result = tool.send_slack_message(message='Test message')
        
        # Verify error result
        assert result['status'] == 'error'
        assert 'Error sending message' in result['error']
    
    def test_create_pagerduty_incident(self, env_setup, mock_clients):
        """Test creating a PagerDuty incident"""
        tool = NotificationTools()
        result = tool.create_pagerduty_incident(
            title='Test Incident',
            description='This is a test incident',
            severity='critical'
        )
        
        # Verify result
        assert result['status'] == 'success'
        assert result['incident_id'] == 'PD1234'
        assert result['incident_url'] == 'https://pagerduty.com/incidents/PD1234'
        
        # Verify incident was created with correct parameters
        mock_clients['pagerduty'].create_incident.assert_called_once()
        call_args = mock_clients['pagerduty'].create_incident.call_args
        assert call_args.kwargs['title'] == 'Test Incident'
        assert call_args.kwargs['description'] == 'This is a test incident'
        assert call_args.kwargs['service'] == 'test-service-id'
        assert call_args.kwargs['urgency'] == 'high'  # 'critical' severity maps to 'high' urgency
    
    def test_create_pagerduty_incident_warning(self, env_setup, mock_clients):
        """Test creating a PagerDuty incident with warning severity"""
        tool = NotificationTools()
        result = tool.create_pagerduty_incident(
            title='Test Warning',
            description='This is a test warning',
            severity='warning'
        )
        
        # Verify urgency is set to 'low' for non-critical severity
        call_args = mock_clients['pagerduty'].create_incident.call_args
        assert call_args.kwargs['urgency'] == 'low'
    
    def test_create_pagerduty_incident_error(self, env_setup, mock_clients):
        """Test error handling when creating PagerDuty incident"""
        # Configure the PagerDuty client to raise an exception
        mock_clients['pagerduty'].create_incident.side_effect = Exception("Error creating incident")
        
        tool = NotificationTools()
        result = tool.create_pagerduty_incident(
            title='Test Incident',
            description='This is a test incident'
        )
        
        # Verify error result
        assert result['status'] == 'error'
        assert 'Error creating incident' in result['error']
    
    def test_send_webex_message(self, env_setup, mock_clients):
        """Test sending a message to Webex Teams"""
        tool = NotificationTools()
        result = tool.send_webex_message(message='Test message')
        
        # Verify result
        assert result['status'] == 'success'
        
        # Verify the message was sent with correct parameters
        mock_clients['webex'].messages.create.assert_called_once()
        call_args = mock_clients['webex'].messages.create.call_args
        assert call_args.kwargs['roomId'] == 'test-room-id'
        assert call_args.kwargs['markdown'] == 'Test message'
    
    def test_send_webex_message_custom_room(self, env_setup, mock_clients):
        """Test sending a message to Webex Teams with custom room"""
        tool = NotificationTools()
        result = tool.send_webex_message(message='Test message', room_id='custom-room-id')
        
        # Verify the message was sent to the custom room
        call_args = mock_clients['webex'].messages.create.call_args
        assert call_args.kwargs['roomId'] == 'custom-room-id'
    
    def test_send_webex_message_error(self, env_setup, mock_clients):
        """Test error handling when sending Webex message"""
        # Configure the Webex client to raise an exception
        mock_clients['webex'].messages.create.side_effect = Exception("Error sending message")
        
        tool = NotificationTools()
        result = tool.send_webex_message(message='Test message')
        
        # Verify error result
        assert result['status'] == 'error'
        assert 'Error sending message' in result['error']
    
    def test_multi_channel_notification(self, env_setup, mock_clients):
        """Test sending notifications to multiple channels"""
        tool = NotificationTools()
        result = tool.send_multi_channel_notification(
            message='Test multi-channel message',
            title='Test Notification',
            send_slack=True,
            send_pagerduty=True,
            severity='warning',
            send_webex=True
        )
        
        # Verify overall result
        assert result['status'] == 'success'
        assert 'error' not in result or result['error'] is None
        assert set(result['channels']) == {'slack', 'pagerduty', 'webex'}
        
        # Verify individual channel results
        assert result['results']['slack']['status'] == 'success'
        assert result['results']['pagerduty']['status'] == 'success'
        assert result['results']['webex']['status'] == 'success'
        
        # Verify that all clients were called
        mock_clients['slack'].chat_postMessage.assert_called_once()
        mock_clients['pagerduty'].create_incident.assert_called_once()
        mock_clients['webex'].messages.create.assert_called_once()
    
    def test_multi_channel_notification_partial_failure(self, env_setup, mock_clients):
        """Test partial failure in multi-channel notification"""
        # Make Webex fail
        mock_clients['webex'].messages.create.side_effect = Exception("Error sending message")
        
        tool = NotificationTools()
        result = tool.send_multi_channel_notification(
            message='Test multi-channel message',
            title='Test Notification',
            send_slack=True,
            send_pagerduty=True,
            send_webex=True
        )
        
        # Verify partial success
        assert result['status'] == 'partial_success'
        assert '1 out of 3 channels failed' in result['error']
        assert result['results']['slack']['status'] == 'success'
        assert result['results']['pagerduty']['status'] == 'success'
        assert result['results']['webex']['status'] == 'error'
    
    def test_multi_channel_notification_all_failure(self, env_setup, mock_clients):
        """Test all channels failing in multi-channel notification"""
        # Make all channels fail
        mock_clients['slack'].chat_postMessage.side_effect = Exception("Slack error")
        mock_clients['pagerduty'].create_incident.side_effect = Exception("PagerDuty error")
        mock_clients['webex'].messages.create.side_effect = Exception("Webex error")
        
        tool = NotificationTools()
        result = tool.send_multi_channel_notification(
            message='Test multi-channel message',
            send_slack=True,
            send_pagerduty=True,
            send_webex=True
        )
        
        # Verify all failure
        assert result['status'] == 'error'
        assert 'All notification channels failed' in result['error']
    
    def test_multi_channel_notification_no_channels(self, env_setup, mock_clients):
        """Test sending multi-channel notification with no channels selected"""
        tool = NotificationTools()
        result = tool.send_multi_channel_notification(
            message='Test message',
            send_slack=False,
            send_pagerduty=False,
            send_webex=False
        )
        
        # Verify error for no channels
        assert result['status'] == 'error'
        assert 'No notification channels were specified' in result['error']
        assert result['channels'] == []