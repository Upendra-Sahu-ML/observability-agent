"""
Configuration for pytest that ensures the root directory is in the Python path.
This allows imports from the 'common' module to work correctly in tests.
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch
from pathlib import Path

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables"""
    with patch.dict(os.environ, {
        'QDRANT_URL': 'http://localhost:6333',
        'WEAVIATE_URL': 'http://localhost:8080',
        'SLACK_BOT_TOKEN': 'test-token',
        'WEBEX_BOT_TOKEN': 'test-token',
        'PAGERDUTY_API_KEY': 'test-token',
        'POSTMORTEM_TEMPLATE_DIR': '/tmp/templates',
        'RUNBOOK_DIR': '/tmp/runbooks'
    }):
        yield

@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client"""
    with patch('qdrant_client.QdrantClient') as mock:
        mock.return_value.get_collection.return_value = Mock()
        mock.return_value.upsert.return_value = Mock()
        mock.return_value.retrieve.return_value = []
        yield mock

@pytest.fixture
def mock_weaviate_client():
    """Mock Weaviate client"""
    with patch('weaviate.Client') as mock:
        mock.return_value.data_object.get_by_id.return_value = None
        yield mock

@pytest.fixture
def mock_slack_client():
    """Mock Slack client"""
    with patch('slack_sdk.WebClient') as mock:
        mock.return_value.chat_postMessage.return_value = {'ok': True}
        yield mock

@pytest.fixture
def mock_webex_client():
    """Mock Webex client"""
    with patch('webexteamssdk.WebexTeamsAPI') as mock:
        mock.return_value.messages.create.return_value = Mock(id='test-message')
        yield mock

@pytest.fixture
def mock_pagerduty_client():
    """Mock PagerDuty client"""
    with patch('pdpyras.APISession') as mock:
        mock.return_value.rpost.return_value = {'id': 'test-incident'}
        mock.return_value.rput.return_value = {'id': 'test-incident'}
        yield mock

@pytest.fixture
def mock_file_operations():
    """Mock file operations"""
    with patch('pathlib.Path.mkdir') as mock_mkdir, \
         patch('pathlib.Path.write_text') as mock_write, \
         patch('pathlib.Path.read_text') as mock_read:
        mock_mkdir.return_value = None
        mock_write.return_value = None
        mock_read.return_value = '# Test Content'
        yield {
            'mkdir': mock_mkdir,
            'write': mock_write,
            'read': mock_read
        }