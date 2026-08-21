"""
Provider Base Class
Unified interface برای همه provider ها
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, AsyncGenerator
import json
from utils.logger import log_info, log_error

class ProviderResponse:
    """Unified response format"""
    def __init__(self, text: str = "", error: Optional[str] = None, done: bool = False):
        self.text = text
        self.error = error
        self.done = done
    
    def to_dict(self) -> Dict:
        result = {}
        if self.text:
            result['text'] = self.text
        if self.error:
            result['error'] = self.error
        if self.done:
            result['done'] = True
        return result

class BaseModelInfo:
    """Unified model info"""
    def __init__(self, id: str, name: str, is_free: bool = False, api_type: str = "messages"):
        self.id = id
        self.name = name
        self.is_free = is_free
        self.api_type = api_type
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'is_free': self.is_free,
            'api': self.api_type
        }

class BaseProvider(ABC):
    """
    Abstract base class for all providers
    Unified interface
    """
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def get_models(self) -> List[BaseModelInfo]:
        """Get available models"""
        pass
    
    @abstractmethod
    def stream_response(self, messages: List[Dict], model: str, api_key: str, **kwargs) -> AsyncGenerator[ProviderResponse, None]:
        """Stream response from model"""
        pass
    
    @abstractmethod
    def analyze_file(self, text: str, model: str, api_key: str, **kwargs) -> str:
        """Analyze file content"""
        pass
    
    def check_health(self) -> bool:
        """Check provider health"""
        try:
            self.get_models()
            return True
        except Exception as e:
            log_error(f"Health check failed for {self.name}: {e}")
            return False