"""
Health Checker with Proper TTL
جلوگیری از stale state
"""
import time
from typing import Dict, Optional
from services.session_pool import session_pool
from config import HEALTH_CHECK_TTL, TIMEOUTS, PROVIDER_PRIORITY
from utils.logger import log_info, log_warning

class HealthStatus:
    """Health status for a provider"""
    def __init__(self):
        self.ok: Optional[bool] = None
        self.last_check: float = 0
        self.error: Optional[str] = None
        self.latency: Optional[float] = None
    
    def is_stale(self) -> bool:
        """Check if status is stale"""
        return (time.time() - self.last_check) > HEALTH_CHECK_TTL
    
    def reset(self):
        """Reset status"""
        self.ok = None
        self.last_check = 0
        self.error = None
        self.latency = None

class HealthChecker:
    """
    Health checker با TTL و proper reset
    """
    def __init__(self):
        self.statuses: Dict[str, HealthStatus] = {
            provider: HealthStatus()
            for provider in PROVIDER_PRIORITY
        }
    
    def check(self, provider: str, force: bool = False) -> bool:
        """
        Check provider health
        با TTL و proper error handling
        """
        status = self.statuses.get(provider)
        
        if not status:
            log_warning(f"Unknown provider: {provider}")
            return False
        
        # Use cache if not stale
        if not force and status.ok is not None and not status.is_stale():
            return status.ok
        
        # Perform check
        start_time = time.time()
        
        try:
            session = session_pool.get_session(provider)
            
            if provider == 'openrouter':
                url = "https://openrouter.ai/api/v1/models"
                resp = session.get(url, timeout=TIMEOUTS['health_check'])
                ok = resp.status_code == 200
            
            elif provider == 'openmodel':
                url = "https://api.openmodel.ai/web/v1/models?page=1&pageSize=1"
                resp = session.get(url, timeout=TIMEOUTS['health_check'])
                ok = resp.status_code == 200
            
            elif provider == 'gemini':
                url = "https://generativelanguage.googleapis.com/"
                resp = session.get(url, timeout=TIMEOUTS['health_check'])
                ok = resp.status_code in [200, 404, 403]
            
            else:
                ok = True
            
            # Update status
            status.ok = ok
            status.last_check = time.time()
            status.latency = time.time() - start_time
            status.error = None if ok else f"HTTP {resp.status_code}"
            
            log_info(f"Health check {provider}: {'OK' if ok else 'FAIL'} ({status.latency:.2f}s)")
            
            return ok
            
        except Exception as e:
            # Proper error handling
            status.ok = False
            status.last_check = time.time()
            status.error = str(e)[:200]
            status.latency = time.time() - start_time
            
            log_warning(f"Health check {provider} failed: {e}")
            
            return False
    
    def get_working_provider(self, preferred: str = 'openrouter') -> str:
        """
        Get working provider with ordered fallback
        بدون set (حفظ ترتیب)
        """
        # Build ordered list
        order = [preferred] + [p for p in PROVIDER_PRIORITY if p != preferred]
        
        # Check each provider
        for provider in order:
            if self.check(provider):
                return provider
        
        # Fallback to preferred
        return preferred
    
    def get_all_statuses(self) -> Dict[str, Dict]:
        """Get all provider statuses"""
        return {
            provider: {
                'ok': status.ok,
                'last_check': status.last_check,
                'error': status.error,
                'latency': status.latency,
                'is_stale': status.is_stale()
            }
            for provider, status in self.statuses.items()
        }
    
    def reset_all(self):
        """Reset all statuses"""
        for status in self.statuses.values():
            status.reset()
        log_info("All health statuses reset")

# Global instance
health_checker = HealthChecker()