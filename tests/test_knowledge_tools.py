import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from common.tools.knowledge_tools import (
    KnowledgeBaseTool,
    PostmortemTemplateTool,
    RunbookUpdateTool
)

# Use module-level patching for notification tools tests
@patch('qdrant_client.QdrantClient')
@patch('common.tools.knowledge_tools.QdrantClient')
@patch('weaviate.Client')
def test_knowledge_base_tool_init(mock_weaviate, mock_qdrant_class, mock_qdrant_import):
    """Test KnowledgeBaseTool initialization with proper mocking"""
    
    os.environ['QDRANT_URL'] = 'http://test-qdrant:6333'
    os.environ['WEAVIATE_URL'] = 'http://test-weaviate:8080'
    
    # Set up mock to prevent actual HTTP connections
    mock_qdrant_instance = MagicMock()
    mock_qdrant_class.return_value = mock_qdrant_instance
    
    # Create the tool
    tool = KnowledgeBaseTool()
    
    # Verify tool has the mocked client
    assert tool.qdrant_client == mock_qdrant_instance
    
    # Verify the client was initialized with the correct URL
    mock_qdrant_class.assert_called_once_with(url='http://test-qdrant:6333')

@patch('qdrant_client.QdrantClient')
@patch('common.tools.knowledge_tools.QdrantClient')
def test_store_incident(mock_qdrant_class, mock_qdrant_import):
    """Test storing an incident with properly mocked client"""
    from common.tools.knowledge_tools import KnowledgeBaseTool
    
    # Set up mock to prevent actual HTTP connections
    mock_qdrant_instance = MagicMock()
    mock_qdrant_class.return_value = mock_qdrant_instance
    
    # Create the tool
    tool = KnowledgeBaseTool()
    
    # Test data
    test_data = {
        'alert_id': 'test-alert',
        'embedding': [0.1, 0.2, 0.3],
        'title': 'Test Incident'
    }
    
    # Execute the store action
    result = tool.execute('store', test_data)
    
    # Verify result and that upsert was called
    assert result['status'] == 'success'
    mock_qdrant_instance.upsert.assert_called_once()

@patch('qdrant_client.QdrantClient')
@patch('common.tools.knowledge_tools.QdrantClient')
def test_retrieve_incident_qdrant(mock_qdrant_class, mock_qdrant_import):
    """Test retrieving an incident with properly mocked client"""
    from common.tools.knowledge_tools import KnowledgeBaseTool
    
    # Set up mock to prevent actual HTTP connections
    mock_qdrant_instance = MagicMock()
    mock_qdrant_class.return_value = mock_qdrant_instance
    
    # Configure mock return value
    mock_point = MagicMock()
    mock_point.payload = {'alert_id': 'test-alert'}
    mock_qdrant_instance.retrieve.return_value = [mock_point]
    
    # Create the tool
    tool = KnowledgeBaseTool()
    
    # Execute the retrieve action
    result = tool.execute('retrieve', {'alert_id': 'test-alert'})
    
    # Verify result
    assert result['status'] == 'success'
    assert result['data']['alert_id'] == 'test-alert'
    mock_qdrant_instance.retrieve.assert_called_once()

@patch('qdrant_client.QdrantClient')
@patch('common.tools.knowledge_tools.QdrantClient')
def test_retrieve_incident_not_found(mock_qdrant_class, mock_qdrant_import):
    """Test retrieving a non-existent incident"""
    from common.tools.knowledge_tools import KnowledgeBaseTool
    
    # Set up mock to prevent actual HTTP connections
    mock_qdrant_instance = MagicMock()
    mock_qdrant_class.return_value = mock_qdrant_instance
    
    # Configure mock to return empty list
    mock_qdrant_instance.retrieve.return_value = []
    
    # Create the tool
    tool = KnowledgeBaseTool()
    
    # Execute the retrieve action
    result = tool.execute('retrieve', {'alert_id': 'nonexistent-alert'})
    
    # Verify result
    assert result['status'] == 'error'
    assert 'not found' in result['error']

@pytest.fixture
def mock_qdrant_client():
    with patch('qdrant_client.QdrantClient') as mock:
        yield mock

@pytest.fixture
def mock_weaviate_client():
    with patch('weaviate.Client') as mock:
        yield mock

class TestKnowledgeBaseTool:
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        # Create proper patch for QdrantClient to prevent actual HTTP requests
        patcher = patch('common.tools.knowledge_tools.QdrantClient', autospec=True)
        self.mock_qdrant = patcher.start()
        
        # Set up mock client to return a mock instance
        self.mock_qdrant_instance = MagicMock()
        self.mock_qdrant.return_value = self.mock_qdrant_instance
        
        # Configure mock to prevent HTTP connections and return expected values
        self.mock_qdrant_instance.get_collection.return_value = Mock()
        self.mock_qdrant_instance.create_collection.return_value = Mock()
        self.mock_qdrant_instance.upsert.return_value = Mock()
        self.mock_qdrant_instance.retrieve.return_value = []
        
        yield
        
        # Stop the patcher after the test
        patcher.stop()
    
    def test_init(self):
        tool = KnowledgeBaseTool()
        assert tool.qdrant_client == self.mock_qdrant.return_value
        self.mock_qdrant.assert_called_once()
    
    def test_store_incident(self):
        tool = KnowledgeBaseTool()
        test_data = {
            'alert_id': 'test-alert',
            'embedding': [0.1, 0.2, 0.3],
            'title': 'Test Incident'
        }
        
        result = tool.execute('store', test_data)
        assert result['status'] == 'success'
        self.mock_qdrant_instance.upsert.assert_called_once()
    
    def test_retrieve_incident_qdrant(self):
        # Set up mock return value for this specific test
        mock_point = MagicMock()
        mock_point.payload = {'alert_id': 'test-alert'}
        self.mock_qdrant_instance.retrieve.return_value = [mock_point]
        
        tool = KnowledgeBaseTool()
        result = tool.execute('retrieve', {'alert_id': 'test-alert'})
        
        assert result['status'] == 'success'
        assert result['data']['alert_id'] == 'test-alert'
        self.mock_qdrant_instance.retrieve.assert_called_once()
    
    def test_retrieve_incident_weaviate(self):
        # Reset mock to return empty for this test
        self.mock_qdrant_instance.retrieve.return_value = []
        
        tool = KnowledgeBaseTool()
        result = tool.execute('retrieve', {'alert_id': 'test-alert'})
        
        # Since Qdrant returns empty and there's no Weaviate integration seen,
        # the result should be an error
        assert result['status'] == 'error'
        assert 'not found' in result['error']
        self.mock_qdrant_instance.retrieve.assert_called_once()

class TestPostmortemTemplateTool:
    def test_get_template(self, tmp_path):
        template_dir = tmp_path / 'templates'
        template_dir.mkdir(exist_ok=True)
        template_file = template_dir / 'default.md'
        template_file.write_text('# Test Template\n{{ title }}')
        
        with patch.dict(os.environ, {'POSTMORTEM_TEMPLATE_DIR': str(template_dir)}):
            tool = PostmortemTemplateTool()
            result = tool.execute('get_template', {'template_name': 'default'})
            assert result['status'] == 'success'
            assert '# Test Template' in result['template']
    
    def test_fill_template(self):
        with patch.dict(os.environ, {'POSTMORTEM_TEMPLATE_DIR': '/tmp/templates'}):
            tool = PostmortemTemplateTool()
            template = '# Test Template\n{{ title }}'
            incident_data = {'title': 'Test Incident'}
            
            result = tool.execute('fill_template', {
                'template': template,
                'incident_data': incident_data
            })
            assert result['status'] == 'success'
            assert 'Test Incident' in result['filled_template']

class TestRunbookUpdateTool:
    def test_update_runbook(self, tmp_path):
        runbook_dir = tmp_path / 'runbooks'
        runbook_dir.mkdir(exist_ok=True)
        runbook_file = runbook_dir / 'test.md'
        runbook_file.write_text('# Test Runbook\n## Recent Incidents')
        
        with patch.dict(os.environ, {'RUNBOOK_DIR': str(runbook_dir)}):
            tool = RunbookUpdateTool()
            result = tool.execute('update', {
                'runbook_name': 'test',
                'incident_data': {
                    'title': 'Test Incident',
                    'timestamp': '2024-03-20',
                    'root_cause': 'Test cause',
                    'resolution': 'Test resolution'
                }
            })
            assert result['status'] == 'success'
            updated_content = runbook_file.read_text()
            assert 'Test Incident' in updated_content
            assert 'Test cause' in updated_content
    
    def test_create_runbook(self, tmp_path):
        runbook_dir = tmp_path / 'runbooks'
        runbook_dir.mkdir(exist_ok=True)
        
        with patch.dict(os.environ, {'RUNBOOK_DIR': str(runbook_dir)}):
            tool = RunbookUpdateTool()
            result = tool.execute('create', {
                'runbook_name': 'new',
                'incident_data': {
                    'title': 'New Incident',
                    'description': 'Test description',
                    'root_cause': 'Test cause',
                    'resolution': 'Test resolution',
                    'alert_id': 'test-alert',
                    'timestamp': '2024-03-20'
                }
            })
            assert result['status'] == 'success'
            runbook_file = runbook_dir / 'new.md'
            assert runbook_file.exists()
            content = runbook_file.read_text()
            assert 'New Incident' in content
            assert 'Test description' in content