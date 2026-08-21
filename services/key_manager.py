"""
API Key Manager v3.0
حفظ کامل تنظیمات Provider شامل protocol و endpoints
"""
import json
import os
import time
from typing import List, Dict, Optional
from utils.logger import log_info, log_error, log_warning

KEYS_FILE = 'api_keys.json'
BACKUP_DIR = 'backups'

# ✅ Preset‌های آماده برای Provider‌های معروف
PROVIDER_PRESETS = {
    'openrouter': {
        'protocol': 'chat_completions',
        'base_url': 'https://openrouter.ai/api/v1',
        'endpoints': {
            'models': '/models',
            'chat': '/chat/completions',
            'test': '/chat/completions'
        },
        'auth': {
            'type': 'bearer',
            'header': 'Authorization',
            'prefix': 'Bearer'
        },
        'headers': {
            'HTTP-Referer': 'http://localhost:5000',
            'X-Title': 'AI Studio Pro'
        }
    },
    'openmodel': {
        'protocol': 'responses',
        'base_url': 'https://api.openmodel.ai',
        'endpoints': {
            'models': '/v1/models',
            'chat': '/v1/responses',
            'test': '/v1/responses'
        },
        'auth': {
            'type': 'bearer',
            'header': 'Authorization',
            'prefix': 'Bearer'
        },
        'headers': {}
    },
    'anthropic': {
        'protocol': 'messages',
        'base_url': 'https://api.anthropic.com',
        'endpoints': {
            'models': '/v1/models',
            'chat': '/v1/messages',
            'test': '/v1/messages'
        },
        'auth': {
            'type': 'api_key',
            'header': 'x-api-key'
        },
        'headers': {
            'anthropic-version': '2023-06-01'
        }
    },
    'gemini': {
        'protocol': 'gemini',
        'base_url': 'https://generativelanguage.googleapis.com',
        'endpoints': {
            'models': '/v1beta/models',
            'chat': '/v1beta/models/{model}:generateContent',
            'test': '/v1beta/models/gemini-2.0-flash:generateContent'
        },
        'auth': {
            'type': 'query',
            'param': 'key'
        },
        'headers': {}
    },
    'openai': {
        'protocol': 'chat_completions',
        'base_url': 'https://api.openai.com/v1',
        'endpoints': {
            'models': '/models',
            'chat': '/chat/completions',
            'test': '/chat/completions'
        },
        'auth': {
            'type': 'bearer',
            'header': 'Authorization',
            'prefix': 'Bearer'
        },
        'headers': {}
    }
}


class KeyManager:
    """مدیریت کامل Providerها و API Keys"""
    
    @staticmethod
    def _ensure_file_exists():
        """ایجاد فایل با ساختار اولیه"""
        if not os.path.exists(KEYS_FILE):
            default_data = {
                "version": "1.0",
                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "providers": []
            }
            
            with open(KEYS_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=2, ensure_ascii=False)
            
            log_info(f"Created {KEYS_FILE}")
    
    @staticmethod
    def _create_backup():
        """ایجاد backup"""
        if not os.path.exists(KEYS_FILE):
            return
        
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"api_keys_{timestamp}.json")
        
        try:
            with open(KEYS_FILE, 'r', encoding='utf-8') as src:
                with open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            
            backups = sorted(os.listdir(BACKUP_DIR))
            if len(backups) > 10:
                for old_backup in backups[:-10]:
                    os.remove(os.path.join(BACKUP_DIR, old_backup))
            
            log_info(f"Backup created: {backup_file}")
        except Exception as e:
            log_error(f"Failed to create backup: {e}")
    
    @staticmethod
    def load_all() -> dict:
        """بارگذاری کل فایل"""
        try:
            KeyManager._ensure_file_exists()
            
            with open(KEYS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'providers' not in data:
                data['providers'] = []
            
            return data
        
        except json.JSONDecodeError as e:
            log_error(f"Invalid JSON: {e}")
            return {"version": "1.0", "providers": []}
        
        except Exception as e:
            log_error(f"Error loading: {e}")
            return {"version": "1.0", "providers": []}
    
    @staticmethod
    def save_all(data: dict) -> bool:
        """ذخیره کل فایل"""
        try:
            KeyManager._create_backup()
            data['last_updated'] = time.strftime("%Y-%m-%dT%H:%M:%S")
            
            with open(KEYS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            log_info(f"Saved {KEYS_FILE}")
            return True
        
        except Exception as e:
            log_error(f"Error saving: {e}")
            return False
    
    @staticmethod
    def get_providers() -> List[Dict]:
        """دریافت همه Providerها"""
        data = KeyManager.load_all()
        return data.get('providers', [])
    
    @staticmethod
    def get_provider(provider_id: str) -> Optional[Dict]:
        """دریافت یک Provider"""
        providers = KeyManager.get_providers()
        for p in providers:
            if p['id'] == provider_id:
                return p
        return None
    
    @staticmethod
    def get_presets() -> Dict:
        """✅ دریافت preset‌های آماده"""
        return PROVIDER_PRESETS
    
    @staticmethod
    def _apply_preset(provider_id: str, provider_data: Dict) -> Dict:
        """✅ اعمال preset بر اساس ID"""
        preset = PROVIDER_PRESETS.get(provider_id.lower())
        
        if preset:
            # ✅ merge preset با داده‌های کاربر
            merged = {**preset, **provider_data}
            
            # اگر کاربر endpoints خاص خود را فرستاده، آن را حفظ کن
            if 'endpoints' in provider_data and provider_data['endpoints']:
                merged['endpoints'] = provider_data['endpoints']
            
            # اگر کاربر headers خاص خود را فرستاده، آن را حفظ کن
            if 'headers' in provider_data and provider_data['headers']:
                merged['headers'] = provider_data['headers']
            
            return merged
        
        return provider_data
    
    @staticmethod
    def _validate_provider_data(provider_data: Dict) -> Optional[str]:
        """اعتبارسنجی داده‌های Provider"""
        if not provider_data.get('id'):
            return "Provider ID is required"
        
        if not provider_data['id'].replace('-', '').replace('_', '').isalnum():
            return "Provider ID must be alphanumeric (can contain hyphens and underscores)"
        
        if not provider_data.get('name'):
            return "Provider Name is required"
        
        base_url = provider_data.get('base_url', '').strip()
        if not base_url:
            return "Base URL is required"
        
        if not base_url.startswith(('http://', 'https://')):
            return f"Base URL must start with http:// or https:// (got: {base_url})"
        
        providers = KeyManager.get_providers()
        for p in providers:
            if p['id'] == provider_data['id']:
                return f"Provider ID '{provider_data['id']}' already exists"
        
        return None
    
    @staticmethod
    def add_provider(provider_data: Dict) -> Dict:
        """✅ اضافه کردن Provider با حفظ کامل تنظیمات"""
        error = KeyManager._validate_provider_data(provider_data)
        if error:
            log_error(f"Validation error: {error}")
            return {'success': False, 'error': error}
        
        data = KeyManager.load_all()
        
        # ✅ اعمال preset بر اساس ID
        provider_data = KeyManager._apply_preset(provider_data['id'], provider_data)
        
        # ✅ ساخت Provider با تمام فیلدها
        provider = {
            'id': provider_data['id'].lower(),
            'name': provider_data['name'],
            'icon': provider_data.get('icon', '🔑'),
            'type': provider_data.get('type', 'openai_compatible'),
            'protocol': provider_data.get('protocol', 'chat_completions'),  # ✅ حفظ protocol
            'base_url': provider_data['base_url'].strip(),
            'endpoints': provider_data.get('endpoints', {  # ✅ حفظ endpoints
                'models': '/models',
                'chat': '/chat/completions',
                'test': '/chat/completions'
            }),
            'auth': provider_data.get('auth', {  # ✅ حفظ auth
                'type': 'bearer',
                'header': 'Authorization',
                'prefix': 'Bearer'
            }),
            'headers': provider_data.get('headers', {}),  # ✅ حفظ headers
            'keys': [],
            'models_cache': [],
            'settings': provider_data.get('settings', {
                'timeout': 30,
                'max_tokens': 2048,
                'temperature': 0.7
            })
        }
        
        data['providers'].append(provider)
        KeyManager.save_all(data)
        
        log_info(f"✅ Added provider: {provider['name']} (protocol: {provider['protocol']})")
        return {'success': True, 'provider': provider}
    
    @staticmethod
    def update_provider(provider_id: str, update_data: Dict) -> bool:
        """به‌روزرسانی Provider با حفظ همه فیلدها"""
        data = KeyManager.load_all()
        
        for i, p in enumerate(data['providers']):
            if p['id'] == provider_id:
                # ✅ حفظ فیلدهای موجود و merge با داده‌های جدید
                updated = {**p, **update_data}
                
                # اگر endpoints ارسال شده، جایگزین کن
                if 'endpoints' in update_data:
                    updated['endpoints'] = update_data['endpoints']
                
                # اگر headers ارسال شده، جایگزین کن
                if 'headers' in update_data:
                    updated['headers'] = update_data['headers']
                
                # اگر auth ارسال شده، جایگزین کن
                if 'auth' in update_data:
                    updated['auth'] = update_data['auth']
                
                data['providers'][i] = updated
                return KeyManager.save_all(data)
        
        return False
    
    @staticmethod
    def delete_provider(provider_id: str) -> bool:
        """حذف Provider"""
        data = KeyManager.load_all()
        data['providers'] = [p for p in data['providers'] if p['id'] != provider_id]
        return KeyManager.save_all(data)
    
    @staticmethod
    def get_keys(provider_id: str) -> List[Dict]:
        """دریافت کلیدهای یک Provider"""
        provider = KeyManager.get_provider(provider_id)
        if not provider:
            return []
        return provider.get('keys', [])
    
    @staticmethod
    def add_key(provider_id: str, key_data: Dict) -> Dict:
        """اضافه کردن کلید"""
        data = KeyManager.load_all()
        
        for i, p in enumerate(data['providers']):
            if p['id'] == provider_id:
                if 'keys' not in p:
                    p['keys'] = []
                
                api_key = key_data.get('api_key', '').strip()
                if not api_key:
                    return {'success': False, 'error': 'API Key is required'}
                
                key = {
                    'id': f"key_{int(time.time())}_{len(p['keys']) + 1}",
                    'name': key_data.get('name', 'Unnamed Key'),
                    'api_key': api_key,
                    'is_default': key_data.get('is_default', False),
                    'enabled': key_data.get('enabled', True),
                    'created_at': time.strftime("%Y-%m-%dT%H:%M:%S"),
                    'last_tested': None,
                    'status': 'unknown'
                }
                
                if key['is_default']:
                    for k in p['keys']:
                        k['is_default'] = False
                
                p['keys'].append(key)
                KeyManager.save_all(data)
                
                log_info(f"Added key to {provider_id}: {key['name']}")
                return {'success': True, 'key': key}
        
        return {'success': False, 'error': 'Provider not found'}
    
    @staticmethod
    def update_key(provider_id: str, key_id: str, update_data: Dict) -> bool:
        """به‌روزرسانی کلید"""
        data = KeyManager.load_all()
        
        for p in data['providers']:
            if p['id'] == provider_id:
                for i, k in enumerate(p.get('keys', [])):
                    if k['id'] == key_id:
                        if update_data.get('is_default', False):
                            for key in p['keys']:
                                key['is_default'] = False
                        
                        p['keys'][i].update(update_data)
                        return KeyManager.save_all(data)
        
        return False
    
    @staticmethod
    def delete_key(provider_id: str, key_id: str) -> bool:
        """حذف کلید"""
        data = KeyManager.load_all()
        
        for p in data['providers']:
            if p['id'] == provider_id:
                p['keys'] = [k for k in p.get('keys', []) if k['id'] != key_id]
                return KeyManager.save_all(data)
        
        return False
    
    @staticmethod
    def get_active_key(provider_id: str) -> Optional[Dict]:
        """دریافت کلید فعال"""
        keys = KeyManager.get_keys(provider_id)
        
        for k in keys:
            if k.get('is_default', False) and k.get('enabled', True):
                return k
        
        for k in keys:
            if k.get('enabled', True):
                return k
        
        return None
    
    @staticmethod
    def get_models_cache(provider_id: str) -> List[Dict]:
        """دریافت cache مدل‌ها"""
        provider = KeyManager.get_provider(provider_id)
        if not provider:
            return []
        return provider.get('models_cache', [])
    
    @staticmethod
    def update_models_cache(provider_id: str, models: List[Dict]) -> bool:
        """به‌روزرسانی cache مدل‌ها"""
        data = KeyManager.load_all()
        
        for p in data['providers']:
            if p['id'] == provider_id:
                p['models_cache'] = [
                    {
                        'id': m['id'],
                        'name': m.get('name', m['id']),
                        'is_free': m.get('is_free', False),
                        'cached_at': time.strftime("%Y-%m-%dT%H:%M:%S")
                    }
                    for m in models
                ]
                return KeyManager.save_all(data)
        
        return False
    
    @staticmethod
    def export_json() -> str:
        """Export به JSON"""
        data = KeyManager.load_all()
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    @staticmethod
    def import_json(json_string: str) -> bool:
        """Import از JSON"""
        try:
            data = json.loads(json_string)
            
            if 'providers' not in data:
                return False
            
            return KeyManager.save_all(data)
        
        except json.JSONDecodeError:
            return False
        
        