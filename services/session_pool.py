"""
HTTP Session Pool
Connection reuse برای performance
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.util.ssl_ import create_urllib3_context
import ssl
from config import TIMEOUTS, RETRY_CONFIG
from utils.logger import log_info

class SessionPool:
    """
    Singleton session pool با connection reuse
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize session pool"""
        self.sessions = {}
        log_info("Session pool initialized")
    
    def get_session(self, provider: str = 'default') -> requests.Session:
        """
        Get or create session for provider
        Connection reuse across requests
        """
        if provider not in self.sessions:
            self.sessions[provider] = self._create_session()
        
        return self.sessions[provider]
    
    def _create_session(self) -> requests.Session:
        """Create session with retry and SSL fix"""
        session = requests.Session()
        
        # Retry strategy
        retry_strategy = Retry(
            total=RETRY_CONFIG['max_retries'],
            backoff_factor=RETRY_CONFIG['backoff_factor'],
            status_forcelist=RETRY_CONFIG['retry_on'],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        # SSL adapter with fix
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        
        # Custom SSL context
        adapter.init_poolmanager = self._custom_init_poolmanager
        
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        
        return session
    
    def _custom_init_poolmanager(self, *args, **kwargs):
        """Custom SSL context to avoid SSL errors"""
        ctx = create_urllib3_context()
        ctx.load_default_certs()
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.maximum_version = ssl.TLSVersion.TLSv1_3
        kwargs['ssl_context'] = ctx
        return super(HTTPAdapter, self).init_poolmanager(*args, **kwargs)
    
    def close_all(self):
        """Close all sessions"""
        for session in self.sessions.values():
            session.close()
        self.sessions.clear()
        log_info("All sessions closed")

# Global instance
session_pool = SessionPool()