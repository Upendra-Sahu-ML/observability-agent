"""
Base class for all agent tools
"""
from abc import ABC, abstractmethod

class AgentTool(ABC):
    """Abstract base class for all agent tools"""
    
    @abstractmethod
    def execute(self, *args, **kwargs):
        """Execute the tool functionality"""
        pass
    
    @property
    @abstractmethod
    def name(self):
        """Return the name of the tool"""
        pass
    
    @property
    @abstractmethod
    def description(self):
        """Return a description of what the tool does"""
        pass