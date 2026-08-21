"""
Input Validation & Security
"""
import re
from urllib.parse import urlparse
from utils.logger import log_warning

ALLOWED_CUSTOM_DOMAINS = [
    'api.openai.com',
    'api.anthropic.com',
    'generativelanguage.googleapis.com',
    'openrouter.ai',
    'api.mistral.ai',
    'api.deepseek.com',
    'api.groq.com',
    'api.together.xyz',
    'api.cohere.ai',
    'api.replicate.com',
    'huggingface.co',
    'api-inference.huggingface.co',
    'inference.dahl.global',
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
]

DISABLE_URL_VALIDATION = False

def validate_url(url: str) -> bool:
    """Validate URL for SSRF protection"""
    if DISABLE_URL_VALIDATION:
        if not url:
            return False
        return url.startswith(('http://', 'https://'))
    
    if not url:
        return False
    
    try:
        parsed = urlparse(url)
        
        if parsed.scheme not in ['http', 'https']:
            log_warning(f"Invalid URL scheme: {parsed.scheme}")
            return False
        
        domain = parsed.netloc.lower()
        
        if ':' in domain:
            domain = domain.split(':')[0]
        
        is_allowed = any(
            domain == allowed or domain.endswith('.' + allowed)
            for allowed in ALLOWED_CUSTOM_DOMAINS
        )
        
        if not is_allowed:
            log_warning(f"Blocked URL: {url} (domain: {domain})")
            return False
        
        return True
        
    except Exception as e:
        log_warning(f"URL validation error: {e}")
        return False

def validate_api_key(key: str, min_length: int = 10) -> bool:
    """Validate API key format"""
    if not key or len(key) < min_length:
        return False
    
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', key):
        return False
    
    return True

def sanitize_text(text: str, max_length: int = 50000) -> str:
    """Sanitize and truncate text"""
    if not text:
        return ""
    
    text = text.replace('\x00', '')
    
    if len(text) > max_length:
        text = text[:max_length]
    
    return text

def validate_provider(provider: str) -> bool:
    """Validate provider name"""
    valid_providers = ['openrouter', 'openmodel', 'openai', 'anthropic', 'gemini', 'custom']
    return provider in valid_providers

def validate_model(model: str) -> bool:
    """Validate model name"""
    if not model:
        return False
    
    if not re.match(r'^[a-zA-Z0-9_\-\.:/]+$', model):
        return False
    
    return True