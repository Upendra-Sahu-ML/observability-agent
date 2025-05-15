import pytest
import logging
from unittest.mock import patch, MagicMock
from common.tools.root_cause_tools import correlation_analysis, dependency_analysis

class TestRootCauseTools:
    
    def test_correlation_analysis_basic(self):
        """Test basic correlation analysis with simple events"""
        # Create test events
        events = [
            {"id": "alert1", "component": "service-a", "timestamp": "2025-05-10T10:00:00Z"},
            {"id": "alert2", "component": "service-a", "timestamp": "2025-05-10T10:01:00Z"},
            {"id": "alert3", "component": "service-b", "timestamp": "2025-05-10T10:02:00Z"},
            {"id": "alert4", "component": "service-c", "timestamp": "2025-05-10T10:03:00Z"},
            {"id": "alert5", "component": "service-c", "timestamp": "2025-05-10T10:04:00Z"}
        ]
        
        # Run correlation analysis
        result = correlation_analysis(events, time_window="10m", correlation_threshold=0.5)
        
        # Check the structure of the result
        assert "correlations" in result
        assert "time_window" in result
        assert "threshold" in result
        assert "components_analyzed" in result
        
        # Check the time window and threshold are correctly set
        assert result["time_window"] == "10m"
        assert result["threshold"] == 0.5
        
        # Check the components analyzed
        assert set(result["components_analyzed"]) == {"service-a", "service-b", "service-c"}
        
        # Check correlations
        correlations = result["correlations"]
        assert "service-a" in correlations
        assert "service-b" in correlations
        assert "service-c" in correlations
    
    def test_correlation_analysis_threshold(self):
        """Test correlation analysis with different thresholds"""
        # Create test events
        events = [
            {"id": "alert1", "component": "service-a", "timestamp": "2025-05-10T10:00:00Z"},
            {"id": "alert2", "component": "service-a", "timestamp": "2025-05-10T10:01:00Z"},
            {"id": "alert3", "component": "service-b", "timestamp": "2025-05-10T10:02:00Z"},
            {"id": "alert4", "component": "service-b", "timestamp": "2025-05-10T10:03:00Z"},
            {"id": "alert5", "component": "service-c", "timestamp": "2025-05-10T10:04:00Z"}
        ]
        
        # Run with low threshold (should find more correlations)
        low_result = correlation_analysis(events, correlation_threshold=0.1)
        
        # Run with high threshold (should find fewer correlations)
        high_result = correlation_analysis(events, correlation_threshold=0.9)
        
        # Check that lower threshold finds more correlations
        low_corr_count = sum(len(comps) for comps in low_result["correlations"].values())
        high_corr_count = sum(len(comps) for comps in high_result["correlations"].values())
        
        # The implementation should generally find more correlations with a lower threshold
        assert low_corr_count >= high_corr_count
    
    def test_correlation_analysis_empty_events(self):
        """Test correlation analysis with empty events list"""
        result = correlation_analysis([])
        
        # Should return an empty result but not error
        assert result["correlations"] == {}
        assert result["components_analyzed"] == []
    
    def test_correlation_analysis_single_component(self):
        """Test correlation analysis with events from a single component"""
        events = [
            {"id": "alert1", "component": "service-a", "timestamp": "2025-05-10T10:00:00Z"},
            {"id": "alert2", "component": "service-a", "timestamp": "2025-05-10T10:01:00Z"},
            {"id": "alert3", "component": "service-a", "timestamp": "2025-05-10T10:02:00Z"}
        ]
        
        result = correlation_analysis(events)
        
        # Should have the component but no correlations (needs multiple components)
        assert "service-a" in result["components_analyzed"]
        assert result["correlations"]["service-a"] == {}
    
    def test_correlation_analysis_missing_component(self):
        """Test correlation analysis with events missing component field"""
        events = [
            {"id": "alert1", "timestamp": "2025-05-10T10:00:00Z"},
            {"id": "alert2", "component": "service-a", "timestamp": "2025-05-10T10:01:00Z"}
        ]
        
        result = correlation_analysis(events)
        
        # Should handle missing components correctly by using "unknown"
        assert "unknown" in result["components_analyzed"]
        assert "service-a" in result["components_analyzed"]
    
    def test_correlation_analysis_exception_handling(self):
        """Test correlation analysis exception handling"""
        # Create malformed events to trigger exception
        events = [{"id": "alert1", "component": None}]  # This should cause attribute error
        
        # Patch the logger to avoid polluting test output
        with patch('common.tools.root_cause_tools.logger') as mock_logger:
            result = correlation_analysis(events)
            
            # Should log the error
            mock_logger.error.assert_called_once()
            
            # Should return error information
            assert "error" in result
    
    def test_dependency_analysis_basic(self):
        """Test basic dependency analysis"""
        services = ["service-a", "service-b", "service-c"]
        
        result = dependency_analysis(services)
        
        # Check the structure of the result
        assert "impact_graph" in result
        assert "services_analyzed" in result
        assert "include_transitive" in result
        
        # Check the services analyzed
        assert set(result["services_analyzed"]) == set(services)
        
        # Check that each service has an entry in the impact graph
        for service in services:
            assert service in result["impact_graph"]
            assert "direct_dependencies" in result["impact_graph"][service]
            assert "dependents" in result["impact_graph"][service]
    
    def test_dependency_analysis_with_data(self):
        """Test dependency analysis with provided dependency data"""
        services = ["service-a", "service-b", "service-c"]
        dependency_data = {
            "service-a": ["service-b", "service-c"],
            "service-b": ["service-c"],
            "service-c": []
        }
        
        result = dependency_analysis(services, dependency_data=dependency_data)
        
        # Check direct dependencies
        assert set(result["impact_graph"]["service-a"]["direct_dependencies"]) == {"service-b", "service-c"}
        assert set(result["impact_graph"]["service-b"]["direct_dependencies"]) == {"service-c"}
        assert result["impact_graph"]["service-c"]["direct_dependencies"] == []
        
        # Check dependents
        assert result["impact_graph"]["service-a"]["dependents"] == []
        assert "service-a" in result["impact_graph"]["service-b"]["dependents"]
        assert "service-a" in result["impact_graph"]["service-c"]["dependents"]
        assert "service-b" in result["impact_graph"]["service-c"]["dependents"]
    
    def test_dependency_analysis_transitive(self):
        """Test dependency analysis with transitive dependencies"""
        services = ["service-a", "service-b", "service-c", "service-d"]
        dependency_data = {
            "service-a": ["service-b"],
            "service-b": ["service-c"],
            "service-c": ["service-d"],
            "service-d": []
        }
        
        # With transitive dependencies
        result_with_transitive = dependency_analysis(
            services, 
            dependency_data=dependency_data,
            include_transitive=True
        )
        
        # Check transitive dependencies
        assert "transitive_dependencies" in result_with_transitive["impact_graph"]["service-a"]
        transitive_deps = result_with_transitive["impact_graph"]["service-a"]["transitive_dependencies"]
        assert set(transitive_deps) == {"service-b", "service-c", "service-d"}
        
        # Without transitive dependencies
        result_without_transitive = dependency_analysis(
            services, 
            dependency_data=dependency_data,
            include_transitive=False
        )
        
        # Should not have transitive dependencies
        assert "transitive_dependencies" not in result_without_transitive["impact_graph"]["service-a"]
    
    def test_dependency_analysis_empty_services(self):
        """Test dependency analysis with empty services list"""
        result = dependency_analysis([])
        
        # Should return an empty result but not error
        assert result["impact_graph"] == {}
        assert result["services_analyzed"] == []
    
    def test_dependency_analysis_exception_handling(self):
        """Test dependency analysis exception handling"""
        # Create malformed dependency data to trigger exception
        services = ["service-a"]
        dependency_data = {"service-a": None}  # This should cause attribute error
        
        # Patch the logger to avoid polluting test output
        with patch('common.tools.root_cause_tools.logger') as mock_logger:
            result = dependency_analysis(services, dependency_data=dependency_data)
            
            # Should log the error
            mock_logger.error.assert_called_once()
            
            # Should return error information
            assert "error" in result