"""
Centralized Configuration with Validation
تنظیمات مرکزی با اعتبارسنجی کامل
"""
import os
import secrets
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

# بارگذاری متغیرهای محیطی (اگر python-dotenv نصب باشد)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv نصب نیست، از env سیستم استفاده می‌شود


class ConfigError(Exception):
    """خطای پیکربندی"""
    pass


@dataclass
class TimeoutConfig:
    """تنظیمات Timeout"""
    health_check: int = 5
    get_models: int = 10
    stream_init: int = 30
    stream_chunk: int = 60
    file_upload: int = 120
    analyze_file: int = 120
    optimize_prompt: int = 30
    
    def validate(self):
        for name, value in self.__dict__.items():
            if not isinstance(value, int) or value <= 0:
                raise ConfigError(f"Invalid timeout for {name}: {value}")


@dataclass
class LimitConfig:
    """تنظیمات محدودیت‌ها"""
    max_file_size_mb: int = 50
    max_context_length: int = 50000
    max_messages: int = 20
    max_tokens: int = 4000
    
    def validate(self):
        if self.max_file_size_mb <= 0:
            raise ConfigError("max_file_size_mb must be positive")
        if self.max_context_length <= 0:
            raise ConfigError("max_context_length must be positive")


@dataclass
class SecurityConfig:
    """تنظیمات امنیتی"""
    secret_key: str = ""
    cors_origins: str = "http://localhost:5000"
    rate_limit_default: str = "100/hour"
    rate_limit_stream: str = "20/minute"
    allowed_domains: list = field(default_factory=lambda: [
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
    ])
    
    def validate(self):
        # ✅ اصلاح: اگر SECRET_KEY نبود، خودکار تولید می‌شود
        if not self.secret_key:
            self.secret_key = secrets.token_hex(32)
            print(f"⚠️ SECRET_KEY not found, generated random key: {self.secret_key[:8]}...")
            print("   For production, set SECRET_KEY in .env file")


@dataclass
class BackupConfig:
    """تنظیمات Backup"""
    enabled: bool = True
    backup_dir: str = "backups"
    max_backups: int = 10
    
    def validate(self):
        if self.max_backups < 0:
            raise ConfigError("max_backups must be non-negative")


@dataclass
class AppConfig:
    """پیکربندی اصلی برنامه"""
    # Flask
    flask_app: str = "app.py"
    flask_env: str = "development"
    flask_debug: bool = True
    host: str = "0.0.0.0"
    port: int = 5000
    
    # API Endpoints
    openmodel_base: str = "https://api.openmodel.ai"
    openrouter_api: str = "https://openrouter.ai/api/v1"
    gemini_api: str = "https://generativelanguage.googleapis.com/v1beta"
    
    # Sub-configs
    timeouts: TimeoutConfig = field(default_factory=TimeoutConfig)
    limits: LimitConfig = field(default_factory=LimitConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    backup: BackupConfig = field(default_factory=BackupConfig)
    
    # API Keys (از environment)
    openrouter_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    mistral_api_key: str = ""
    
    # Free Models
    free_model_indicators: list = field(default_factory=lambda: [
        ':free', 'flash', 'mini', 'free'
    ])
    
    # Provider Priority
    provider_priority: list = field(default_factory=lambda: [
        'openrouter', 'openmodel', 'gemini'
    ])
    
    # Allowed Extensions
    allowed_extensions: set = field(default_factory=lambda: {
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'
    })
    
    def validate(self):
        self.timeouts.validate()
        self.limits.validate()
        self.security.validate()
        self.backup.validate()
        
        if self.port < 1 or self.port > 65535:
            raise ConfigError(f"Invalid port: {self.port}")
        
        return True


def load_config() -> AppConfig:
    """بارگذاری و اعتبارسنجی پیکربندی"""
    config = AppConfig()
    
    # Flask
    config.flask_app = os.getenv('FLASK_APP', config.flask_app)
    config.flask_env = os.getenv('FLASK_ENV', config.flask_env)
    config.flask_debug = os.getenv('FLASK_DEBUG', '1') == '1'
    config.host = os.getenv('HOST', config.host)
    config.port = int(os.getenv('PORT', str(config.port)))
    
    # Security
    config.security.secret_key = os.getenv('SECRET_KEY', config.security.secret_key)
    config.security.cors_origins = os.getenv('CORS_ORIGINS', config.security.cors_origins)
    config.security.rate_limit_default = os.getenv('RATE_LIMIT_DEFAULT', config.security.rate_limit_default)
    config.security.rate_limit_stream = os.getenv('RATE_LIMIT_STREAM', config.security.rate_limit_stream)
    
    # API Keys
    config.openrouter_api_key = os.getenv('OPENROUTER_API_KEY', '')
    config.openai_api_key = os.getenv('OPENAI_API_KEY', '')
    config.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY', '')
    config.gemini_api_key = os.getenv('GEMINI_API_KEY', '')
    config.mistral_api_key = os.getenv('MISTRAL_API_KEY', '')
    
    # Timeouts
    config.timeouts.health_check = int(os.getenv('TIMEOUT_HEALTH_CHECK', config.timeouts.health_check))
    config.timeouts.get_models = int(os.getenv('TIMEOUT_GET_MODELS', config.timeouts.get_models))
    config.timeouts.stream_init = int(os.getenv('TIMEOUT_STREAM_INIT', config.timeouts.stream_init))
    config.timeouts.stream_chunk = int(os.getenv('TIMEOUT_STREAM_CHUNK', config.timeouts.stream_chunk))
    config.timeouts.file_upload = int(os.getenv('TIMEOUT_FILE_UPLOAD', config.timeouts.file_upload))
    config.timeouts.analyze_file = int(os.getenv('TIMEOUT_ANALYZE_FILE', config.timeouts.analyze_file))
    
    # Limits
    config.limits.max_file_size_mb = int(os.getenv('MAX_FILE_SIZE_MB', config.limits.max_file_size_mb))
    config.limits.max_context_length = int(os.getenv('MAX_CONTEXT_LENGTH', config.limits.max_context_length))
    config.limits.max_messages = int(os.getenv('MAX_MESSAGES', config.limits.max_messages))
    config.limits.max_tokens = int(os.getenv('MAX_TOKENS', config.limits.max_tokens))
    
    # Backup
    config.backup.enabled = os.getenv('BACKUP_ENABLED', 'true').lower() == 'true'
    config.backup.backup_dir = os.getenv('BACKUP_DIR', config.backup.backup_dir)
    config.backup.max_backups = int(os.getenv('MAX_BACKUPS', config.backup.max_backups))
    
    # اعتبارسنجی
    config.validate()
    
    return config


# ایجاد instance جهانی
try:
    CONFIG = load_config()
except ConfigError as e:
    print(f"❌ Configuration Error: {e}")
    print("Please check your .env file")
    raise


# سازگاری با کد قدیمی
TIMEOUTS = {
    'health_check': CONFIG.timeouts.health_check,
    'get_models': CONFIG.timeouts.get_models,
    'stream_init': CONFIG.timeouts.stream_init,
    'stream_chunk': CONFIG.timeouts.stream_chunk,
    'file_upload': CONFIG.timeouts.file_upload,
    'analyze_file': CONFIG.timeouts.analyze_file,
    'optimize_prompt': CONFIG.timeouts.optimize_prompt,
}

RETRY_CONFIG = {
    'max_retries': 3,
    'backoff_factor': 2,
    'retry_on': [429, 500, 502, 503, 504],
}

CONTEXT_LIMITS = {
    'max_tokens': CONFIG.limits.max_tokens,
    'max_messages': CONFIG.limits.max_messages,
    'max_text_length': CONFIG.limits.max_context_length,
}

HEALTH_CHECK_TTL = 300

ALLOWED_CUSTOM_DOMAINS = CONFIG.security.allowed_domains

MAX_FILE_SIZE = CONFIG.limits.max_file_size_mb * 1024 * 1024
ALLOWED_EXTENSIONS = CONFIG.allowed_extensions

FREE_MODEL_INDICATORS = CONFIG.free_model_indicators
PROVIDER_PRIORITY = CONFIG.provider_priority

OPENMODEL_BASE = CONFIG.openmodel_base
OPENROUTER_API = CONFIG.openrouter_api
GEMINI_API = CONFIG.gemini_api