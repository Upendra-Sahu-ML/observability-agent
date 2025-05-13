import os
import pytest
from unittest.mock import Mock, patch, MagicMock

class TestSlackNotificationTool:
    def test_init(self):
        """Test the initialization of SlackNotificationTool"""
        from common.tools.notification_tools import SlackNotificationTool
        
        with patch.dict(os.environ, {'SLACK_BOT_TOKEN': 'test-token'}):
            with patch('common.tools.notification_tools.WebClient') as mock_client:
                # Configure the mock to return itself when instantiated
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance
                
                # Create the tool
                tool = SlackNotificationTool()
                
                # Verify tool has the mocked client
                assert tool.client == mock_instance
                assert tool.slack_token == 'test-token'
    
    def test_execute(self):
        """Test sending a message with SlackNotificationTool"""
        from common.tools.notification_tools import SlackNotificationTool
        
        with patch.dict(os.environ, {'SLACK_BOT_TOKEN': 'test-token'}):
            with patch('common.tools.notification_tools.WebClient') as mock_client:
                # Configure the mock
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance
                mock_instance.chat_postMessage.return_value = {'ok': True}
                
                # Create the tool
                tool = SlackNotificationTool()
                
                # Send a message
                result = tool.execute(message='Test message', channel='#test')
                
                # Verify result
                assert result['status'] == 'success'
                mock_instance.chat_postMessage.assert_called_once()
                
                # Get the call args
                call_args = mock_instance.chat_postMessage.call_args
                assert call_args.kwargs['channel'] == '#test'
                assert call_args.kwargs['text'] == 'Test message'
    
    def test_execute_with_default_channel(self):
        """Test sending a message with SlackNotificationTool using default channel"""
        from common.tools.notification_tools import SlackNotificationTool
        
        with patch.dict(os.environ, {
            'SLACK_BOT_TOKEN': 'test-token',
            'SLACK_DEFAULT_CHANNEL': '#default'
        }):
            with patch('common.tools.notification_tools.WebClient') as mock_client:
                # Configure the mock
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance
                mock_instance.chat_postMessage.return_value = {'ok': True}
                
                # Create the tool
                tool = SlackNotificationTool()
                
                # Send a message without specifying channel
                result = tool.execute(message='Test message')
                
                # Verify result
                assert result['status'] == 'success'
                mock_instance.chat_postMessage.assert_called_once()
                
                # Get the call args
                call_args = mock_instance.chat_postMessage.call_args
                assert call_args.kwargs['channel'] == '#default'
                assert call_args.kwargs['text'] == 'Test message'
    
    def test_error_handling(self):
        """Test error handling in SlackNotificationTool"""
        from common.tools.notification_tools import SlackNotificationTool
        
        with patch.dict(os.environ, {'SLACK_BOT_TOKEN': 'test-token'}):
            with patch('common.tools.notification_tools.WebClient') as mock_client:
                # Configure the mock to raise an exception
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance
                
                from slack_sdk.errors import SlackApiError
                mock_instance.chat_postMessage.side_effect = SlackApiError("Error sending message", {"error": "channel_not_found"})
                
                # Create the tool
                tool = SlackNotificationTool()
                
                # Send a message
                result = tool.execute(message='Test message', channel='#test')
                
                # Verify result
                assert result['status'] == 'error'
                assert 'Error sending message' in result['error']

class TestWebexNotificationTool:
    def test_init(self):
        """Test the initialization of WebexNotificationTool"""
        from common.tools.notification_tools import WebexNotificationTool
        
        with patch.dict(os.environ, {'WEBEX_ACCESS_TOKEN': 'test-token'}):
            with patch('common.tools.notification_tools.WebexTeamsAPI') as mock_api:
                # Configure the mock to return itself when instantiated
                mock_instance = MagicMock()
                mock_api.return_value = mock_instance
                
                # Create the tool
                tool = WebexNotificationTool()
                
                # Verify tool has the mocked client
                assert tool.client == mock_instance
                assert tool.access_token == 'test-token'
    
    def test_execute(self):
        """Test sending a message with WebexNotificationTool"""
        from common.tools.notification_tools import WebexNotificationTool
        
        with patch.dict(os.environ, {'WEBEX_ACCESS_TOKEN': 'test-token'}):
            with patch('common.tools.notification_tools.WebexTeamsAPI') as mock_api:
                # Configure the mock
                mock_instance = MagicMock()
                mock_api.return_value = mock_instance
                mock_instance.messages.create.return_value = {'id': 'test-message-id'}
                
                # Create the tool
                tool = WebexNotificationTool()
                
                # Send a message
                result = tool.execute(message='Test message', room_id='test-room')
                
                # Verify result
                assert result['status'] == 'success'
                mock_instance.messages.create.assert_called_once()
                
                # Get the call args
                call_args = mock_instance.messages.create.call_args
                assert call_args.kwargs['roomId'] == 'test-room'
                assert call_args.kwargs['markdown'] == 'Test message'
    
    def test_execute_with_default_room(self):
        """Test sending a message with WebexNotificationTool using default room"""
        from common.tools.notification_tools import WebexNotificationTool
        
        with patch.dict(os.environ, {
            'WEBEX_ACCESS_TOKEN': 'test-token',
            'WEBEX_DEFAULT_ROOM_ID': 'default-room'
        }):
            with patch('common.tools.notification_tools.WebexTeamsAPI') as mock_api:
                # Configure the mock
                mock_instance = MagicMock()
                mock_api.return_value = mock_instance
                mock_instance.messages.create.return_value = {'id': 'test-message-id'}
                
                # Create the tool
                tool = WebexNotificationTool()
                
                # Send a message without specifying room
                result = tool.execute(message='Test message')
                
                # Verify result
                assert result['status'] == 'success'
                mock_instance.messages.create.assert_called_once()
                
                # Get the call args
                call_args = mock_instance.messages.create.call_args
                assert call_args.kwargs['roomId'] == 'default-room'
                assert call_args.kwargs['markdown'] == 'Test message'
    
    def test_error_handling(self):
        """Test error handling in WebexNotificationTool"""
        from common.tools.notification_tools import WebexNotificationTool
        
        with patch.dict(os.environ, {'WEBEX_ACCESS_TOKEN': 'test-token'}):
            with patch('common.tools.notification_tools.WebexTeamsAPI') as mock_api:
                # Configure the mock to raise an exception
                mock_instance = MagicMock()
                mock_api.return_value = mock_instance
                mock_instance.messages.create.side_effect = Exception("Error sending message")
                
                # Create the tool
                tool = WebexNotificationTool()
                
                # Send a message
                result = tool.execute(message='Test message', room_id='test-room')
                
                # Verify result
                assert result['status'] == 'error'
                assert 'Error sending message' in result['error']

class TestPagerDutyNotificationTool:
    def test_init(self):
        """Test the initialization of PagerDutyNotificationTool"""
        from common.tools.notification_tools import PagerDutyNotificationTool
        
        with patch.dict(os.environ, {
            'PAGERDUTY_API_TOKEN': 'test-token',
            'PAGERDUTY_SERVICE_ID': 'test-service'
        }):
            with patch('common.tools.notification_tools.PagerDutyClient') as mock_client:
                # Create the tool
                tool = PagerDutyNotificationTool()
                
                # Verify tool has the mocked client
                assert tool.client == mock_client.return_value
                assert tool.api_token == 'test-token'
                assert tool.service_id == 'test-service'
    
    def test_execute(self):
        """Test creating an incident with PagerDutyNotificationTool"""
        from common.tools.notification_tools import PagerDutyNotificationTool
        
        with patch.dict(os.environ, {
            'PAGERDUTY_API_TOKEN': 'test-token',
            'PAGERDUTY_SERVICE_ID': 'test-service'
        }):
            with patch('common.tools.notification_tools.PagerDutyClient') as mock_client:
                # Configure the mock
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance
                mock_instance.create_incident.return_value = {'id': 'test-incident-id'}
                
                # Create the tool
                tool = PagerDutyNotificationTool()
                
                # Create an incident
                result = tool.execute(
                    title='Test Incident',
                    description='Test Description',
                    severity='critical'
                )
                
                # Verify result
                assert result['status'] == 'success'
                mock_instance.create_incident.assert_called_once()
                
                # Get the call args
                call_args = mock_instance.create_incident.call_args
                assert call_args.kwargs['title'] == 'Test Incident'
                assert call_args.kwargs['description'] == 'Test Description'
                assert call_args.kwargs['service'] == 'test-service'
                assert call_args.kwargs['urgency'] == 'high'  # critical gets mapped to high
    
    def test_error_handling(self):
        """Test error handling in PagerDutyNotificationTool"""
        from common.tools.notification_tools import PagerDutyNotificationTool
        
        with patch.dict(os.environ, {
            'PAGERDUTY_API_TOKEN': 'test-token',
            'PAGERDUTY_SERVICE_ID': 'test-service'
        }):
            with patch('common.tools.notification_tools.PagerDutyClient') as mock_client:
                # Configure the mock to raise an exception
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance
                mock_instance.create_incident.side_effect = Exception("Error creating incident")
                
                # Create the tool
                tool = PagerDutyNotificationTool()
                
                # Create an incident
                result = tool.execute(
                    title='Test Incident',
                    description='Test Description'
                )
                
                # Verify result
                assert result['status'] == 'error'
                assert 'Error creating incident' in result['error']