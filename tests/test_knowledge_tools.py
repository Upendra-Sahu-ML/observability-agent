import os
import pytest
from unittest.mock import Mock, patch
from common.tools.knowledge_tools import (
    KnowledgeBaseTool,
    PostmortemTemplateTool,
    RunbookUpdateTool
)

@pytest.fixture
def mock_qdrant_client():
    with patch('qdrant_client.QdrantClient') as mock:
        yield mock

@pytest.fixture
def mock_weaviate_client():
    with patch('weaviate.Client') as mock:
        yield mock

class TestKnowledgeBaseTool:
    def test_init(self, mock_qdrant_client, mock_weaviate_client):
        os.environ['QDRANT_URL'] = 'http://test-qdrant:6333'
        os.environ['WEAVIATE_URL'] = 'http://test-weaviate:8080'
        
        tool = KnowledgeBaseTool()
        assert tool.qdrant_client == mock_qdrant_client.return_value
        assert tool.weaviate_client == mock_weaviate_client.return_value
    
    def test_store_incident(self, mock_qdrant_client, mock_weaviate_client):
        tool = KnowledgeBaseTool()
        test_data = {
            'alert_id': 'test-alert',
            'embedding': [0.1, 0.2, 0.3],
            'title': 'Test Incident'
        }
        
        result = tool.execute('store', test_data)
        assert result['status'] == 'success'
        mock_qdrant_client.return_value.upsert.assert_called_once()
        mock_weaviate_client.return_value.data_object.create.assert_called_once()
    
    def test_retrieve_incident_qdrant(self, mock_qdrant_client, mock_weaviate_client):
        tool = KnowledgeBaseTool()
        mock_qdrant_client.return_value.retrieve.return_value = [Mock(payload={'alert_id': 'test-alert'})]
        
        result = tool.execute('retrieve', {'alert_id': 'test-alert'})
        assert result['status'] == 'success'
        assert result['data']['alert_id'] == 'test-alert'
    
    def test_retrieve_incident_weaviate(self, mock_qdrant_client, mock_weaviate_client):
        tool = KnowledgeBaseTool()
        mock_qdrant_client.return_value.retrieve.return_value = []
        mock_weaviate_client.return_value.data_object.get_by_id.return_value = {'alert_id': 'test-alert'}
        
        result = tool.execute('retrieve', {'alert_id': 'test-alert'})
        assert result['status'] == 'success'
        assert result['data']['alert_id'] == 'test-alert'

class TestPostmortemTemplateTool:
    @pytest.fixture
    def tool(self):
        os.environ['POSTMORTEM_TEMPLATE_DIR'] = '/tmp/templates'
        return PostmortemTemplateTool()
    
    def test_get_template(self, tool, tmp_path):
        template_dir = tmp_path / 'templates'
        template_dir.mkdir()
        template_file = template_dir / 'default.md'
        template_file.write_text('# Test Template\n{{ title }}')
        
        with patch('os.environ.get', return_value=str(template_dir)):
            result = tool.execute('get_template', {'template_name': 'default'})
            assert result['status'] == 'success'
            assert '# Test Template' in result['template']
    
    def test_fill_template(self, tool):
        template = '# Test Template\n{{ title }}'
        incident_data = {'title': 'Test Incident'}
        
        result = tool.execute('fill_template', {
            'template': template,
            'incident_data': incident_data
        })
        assert result['status'] == 'success'
        assert 'Test Incident' in result['filled_template']

class TestRunbookUpdateTool:
    @pytest.fixture
    def tool(self):
        os.environ['RUNBOOK_DIR'] = '/tmp/runbooks'
        return RunbookUpdateTool()
    
    def test_update_runbook(self, tool, tmp_path):
        runbook_dir = tmp_path / 'runbooks'
        runbook_dir.mkdir()
        runbook_file = runbook_dir / 'test.md'
        runbook_file.write_text('# Test Runbook\n## Recent Incidents')
        
        with patch('os.environ.get', return_value=str(runbook_dir)):
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
    
    def test_create_runbook(self, tool, tmp_path):
        runbook_dir = tmp_path / 'runbooks'
        runbook_dir.mkdir()
        
        with patch('os.environ.get', return_value=str(runbook_dir)):
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