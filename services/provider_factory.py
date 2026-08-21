"""
Provider Factory v3.0
پشتیبانی از پروتکل‌های مختلف:
- responses (OpenAI جدید)
- messages (Anthropic/Claude)
- chat_completions (OpenAI قدیمی)
- gemini (Google)
"""
import requests
import json
from typing import List, Dict, Optional, AsyncGenerator
from services.key_manager import KeyManager
from utils.logger import log_info, log_error, log_warning


# ============ Response Class ============

class Response:
    """کلاس استاندارد برای پاسخ‌های stream"""
    
    def __init__(self, text: str = '', done: bool = False, error: str = None):
        self.text = text
        self.done = done
        self.error = error
    
    def to_dict(self) -> Dict:
        result = {}
        if self.text:
            result['text'] = self.text
        if self.done:
            result['done'] = True
        if self.error:
            result['error'] = self.error
        return result
    
    def __repr__(self):
        return f"Response(text='{self.text[:50]}', done={self.done}, error={self.error})"


# ============ Provider Adapter ============

class ProviderAdapter:
    """Adapter یکپارچه برای همه Providerها با پشتیبانی از پروتکل‌های مختلف"""
    
    def __init__(self, provider_config: Dict):
        self.config = provider_config
        self.id = provider_config['id']
        self.name = provider_config['name']
        self.type = provider_config.get('type', 'openai_compatible')
        self.protocol = provider_config.get('protocol', 'chat_completions')  # ✅ پروتکل جدید
        self.base_url = provider_config.get('base_url', '').rstrip('/')
        self.endpoints = provider_config.get('endpoints', {})
        self.auth = provider_config.get('auth', {})
        self.headers = provider_config.get('headers', {})
        self.settings = provider_config.get('settings', {})
        
        log_info(f"🔧 Initialized provider: {self.name} (protocol: {self.protocol})")
    
    def _build_headers(self, api_key: str) -> Dict:
        """ساخت headers کامل بر اساس نوع Provider"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        if self.headers:
            headers.update(self.headers)
        
        auth_type = self.auth.get('type', 'bearer')
        
        if auth_type == 'bearer':
            header_name = self.auth.get('header', 'Authorization')
            prefix = self.auth.get('prefix', 'Bearer')
            headers[header_name] = f"{prefix} {api_key}"
        
        elif auth_type == 'api_key':
            header_name = self.auth.get('header', 'X-API-Key')
            headers[header_name] = api_key
        
        # Headerهای اجباری OpenRouter
        if 'openrouter' in self.base_url.lower() or self.id == 'openrouter':
            if 'HTTP-Referer' not in headers:
                headers['HTTP-Referer'] = 'http://localhost:5000'
            if 'X-Title' not in headers:
                headers['X-Title'] = 'AI Studio Pro'
        
        return headers
    
    def _get_smart_max_tokens(self, model: str) -> int:
        """تعیین هوشمند max_tokens"""
        
        if 'max_tokens' in self.settings:
            configured = self.settings['max_tokens']
            if configured and configured > 0:
                return configured
        
        if ':free' in model:
            return 1024
        
        free_indicators = ['-free', ':free', 'free-', '/free']
        if any(ind in model.lower() for ind in free_indicators):
            return 1024
        
        small_models = ['mini', 'nano', 'flash', 'lite', 'small']
        if any(ind in model.lower() for ind in small_models):
            return 2048
        
        return 2048
    
    def _get_chat_endpoint(self) -> str:
        """✅ دریافت endpoint صحیح بر اساس پروتکل"""
        
        # اگر در config تعریف شده باشد
        if 'chat' in self.endpoints:
            return self.endpoints['chat']
        
        # بر اساس پروتکل
        if self.protocol == 'responses':
            return '/v1/responses'
        elif self.protocol == 'messages':
            return '/v1/messages'
        elif self.protocol == 'gemini':
            return '/v1beta/models/{model}:generateContent'
        else:  # chat_completions (پیش‌فرض)
            return '/v1/chat/completions'
    
    def _build_url(self, endpoint_key: str, model: str = None) -> str:
        """ساخت URL کامل"""
        
        if endpoint_key == 'chat':
            endpoint = self._get_chat_endpoint()
        else:
            endpoint = self.endpoints.get(endpoint_key, '')
        
        if model:
            endpoint = endpoint.replace('{model}', model)
        
        url = self.base_url + endpoint
        
        if self.auth.get('type') == 'query':
            param_name = self.auth.get('param', 'key')
            active_key = KeyManager.get_active_key(self.id)
            if active_key:
                url += f"?{param_name}={active_key['api_key']}"
        
        return url
    
    def _build_payload(self, messages: List[Dict], model: str, max_tokens: int) -> Dict:
        """✅ ساخت payload بر اساس پروتکل"""
        
        if self.protocol == 'responses':
            # OpenAI Responses API
            return {
                'model': model,
                'input': messages,  # آرایه پیام‌ها
                'stream': True,
                'max_output_tokens': max_tokens,
                'temperature': self.settings.get('temperature', 0.7)
            }
        
        elif self.protocol == 'messages':
            # Anthropic Messages API
            # استخراج system message
            system_msg = None
            user_messages = []
            
            for msg in messages:
                if msg['role'] == 'system':
                    system_msg = msg['content']
                else:
                    user_messages.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })
            
            payload = {
                'model': model,
                'messages': user_messages,
                'max_tokens': max_tokens,
                'stream': True,
                'temperature': self.settings.get('temperature', 0.7)
            }
            
            if system_msg:
                payload['system'] = system_msg
            
            return payload
        
        elif self.protocol == 'gemini':
            # Google Gemini API
            return {
                'contents': [{'parts': [{'text': m['content']}]} for m in messages if m['role'] == 'user'],
                'generationConfig': {
                    'temperature': self.settings.get('temperature', 0.7),
                    'maxOutputTokens': max_tokens
                }
            }
        
        else:  # chat_completions
            # OpenAI Chat Completions API (قدیمی)
            return {
                'model': model,
                'messages': messages,
                'temperature': self.settings.get('temperature', 0.7),
                'max_tokens': max_tokens,
                'stream': True
            }
    
    def _parse_stream_response(self, data: Dict) -> Optional[str]:
        """✅ Parse پاسخ stream بر اساس پروتکل"""
        
        if self.protocol == 'responses':
            # OpenAI Responses API
            if 'delta' in data:
                return data['delta'].get('content', '')
            elif 'output' in data and len(data['output']) > 0:
                return data['output'][0].get('text', '')
        
        elif self.protocol == 'messages':
            # Anthropic Messages API
            if 'delta' in data:
                return data['delta'].get('text', '')
            elif 'completion' in data:
                return data['completion']
        
        elif self.protocol == 'gemini':
            # Google Gemini API
            if 'candidates' in data:
                parts = data['candidates'][0].get('content', {}).get('parts', [])
                for part in parts:
                    text = part.get('text', '')
                    if text:
                        return text
        
        else:  # chat_completions
            # OpenAI Chat Completions API
            if 'choices' in data:
                delta = data['choices'][0].get('delta', {})
                return delta.get('content', '')
        
        return None
    
    def fetch_models(self) -> List[Dict]:
        """دریافت لیست مدل‌ها از API"""
        log_info(f"Fetching models for {self.name} ({self.id})")
        
        active_key = KeyManager.get_active_key(self.id)
        if not active_key:
            log_warning(f"No active key for {self.name}")
            return []
        
        try:
            url = self._build_url('models')
            headers = self._build_headers(active_key['api_key'])
            timeout = self.settings.get('timeout', 30)
            
            log_info(f"Requesting: {url}")
            
            resp = requests.get(url, headers=headers, timeout=timeout)
            
            if resp.status_code != 200:
                log_error(f"Failed to fetch models: HTTP {resp.status_code}")
                log_error(f"Response: {resp.text[:500]}")
                return []
            
            content_type = resp.headers.get('Content-Type', '')
            if 'application/json' not in content_type and 'text/json' not in content_type:
                log_error(f"Response is not JSON. Content-Type: {content_type}")
                return []
            
            if not resp.text.strip():
                log_error(f"Empty response from {url}")
                return []
            
            try:
                data = resp.json()
            except json.JSONDecodeError as e:
                log_error(f"JSON decode error: {e}")
                return []
            
            if self.type == 'openai_compatible':
                models = self._parse_openai_models(data)
            elif self.type == 'gemini':
                models = self._parse_gemini_models(data)
            else:
                models = self._parse_generic_models(data)
            
            log_info(f"✅ Parsed {len(models)} models for {self.name}")
            return models
        
        except requests.exceptions.Timeout:
            log_error(f"Timeout fetching models for {self.name}")
            return []
        
        except requests.exceptions.RequestException as e:
            log_error(f"Request error for {self.name}: {e}")
            return []
        
        except Exception as e:
            log_error(f"Unexpected error fetching models for {self.name}: {e}", exc_info=True)
            return []
    
    def _parse_openai_models(self, data: Dict) -> List[Dict]:
        """Parsing مدل‌های OpenAI-compatible"""
        models = []
        
        if 'data' in data:
            for m in data['data']:
                model_id = m.get('id', '')
                name = m.get('name', model_id)
                is_free = any(ind in model_id.lower() for ind in [':free', 'free', 'flash', 'mini'])
                
                models.append({
                    'id': model_id,
                    'name': name,
                    'is_free': is_free
                })
        
        elif 'models' in data:
            for m in data['models']:
                model_id = m.get('id', m.get('name', ''))
                models.append({
                    'id': model_id,
                    'name': m.get('name', model_id),
                    'is_free': False
                })
        
        return models
    
    def _parse_gemini_models(self, data: Dict) -> List[Dict]:
        """Parsing مدل‌های Gemini"""
        models = []
        
        for m in data.get('models', []):
            model_id = m.get('name', '').replace('models/', '')
            display_name = m.get('displayName', model_id)
            is_free = 'flash' in model_id.lower() or 'free' in model_id.lower()
            
            models.append({
                'id': model_id,
                'name': display_name,
                'is_free': is_free
            })
        
        return models
    
    def _parse_generic_models(self, data: Dict) -> List[Dict]:
        """Parsing عمومی"""
        models = []
        items = data.get('data', data.get('models', []))
        
        if isinstance(items, list):
            for m in items:
                if isinstance(m, dict):
                    model_id = m.get('id', m.get('name', ''))
                    if model_id:
                        models.append({
                            'id': model_id,
                            'name': m.get('name', model_id),
                            'is_free': False
                        })
        
        return models
    
    async def stream_response(self, messages: List[Dict], model: str, api_key: str, 
                             custom_url: str = None) -> AsyncGenerator[Response, None]:
        """Stream response با پشتیبانی از پروتکل‌های مختلف"""
        try:
            url = custom_url or self._build_url('chat', model)
            headers = self._build_headers(api_key)
            timeout = self.settings.get('timeout', 30)
            
            max_tokens = self._get_smart_max_tokens(model)
            
            # ✅ ساخت payload بر اساس پروتکل
            payload = self._build_payload(messages, model, max_tokens)
            
            log_info(f"📡 Streaming from: {url}")
            log_info(f"🤖 Model: {model}")
            log_info(f"🎯 Protocol: {self.protocol}")
            log_info(f"🎯 max_tokens: {max_tokens}")
            log_info(f"📋 Headers: {list(headers.keys())}")
            log_info(f"📦 Payload keys: {list(payload.keys())}")
            
            resp = requests.post(url, json=payload, headers=headers, stream=True, timeout=timeout)
            
            if resp.status_code != 200:
                log_error(f"❌ Stream HTTP error: {resp.status_code}")
                log_error(f"📄 Response: {resp.text[:500]}")
                
                error_msg = self._format_error_message(resp.status_code, resp.text)
                yield Response(error=error_msg)
                return
            
            log_info(f"✅ Stream started, status: {resp.status_code}")
            
            for chunk in resp.iter_lines():
                if not chunk:
                    continue
                
                line = chunk.decode('utf-8', errors='replace').strip()
                
                if not line.startswith('data: '):
                    continue
                
                raw = line[6:]
                
                if raw == '[DONE]':
                    log_info("✅ Stream [DONE] received")
                    yield Response(done=True)
                    return
                
                try:
                    data = json.loads(raw)
                    
                    # ✅ Parse بر اساس پروتکل
                    text = self._parse_stream_response(data)
                    
                    if text:
                        yield Response(text=text)
                
                except json.JSONDecodeError as e:
                    log_warning(f"⚠️ JSON decode error in stream: {e}")
                    continue
        
        except requests.exceptions.Timeout:
            log_error(f"⏱️ Stream timeout for {self.name}")
            yield Response(error="⏱️ Request timeout - please try again")
        
        except requests.exceptions.RequestException as e:
            log_error(f"❌ Stream request error: {e}")
            yield Response(error=f"🌐 Network error: {str(e)}")
        
        except Exception as e:
            log_error(f"❌ Unexpected stream error: {e}", exc_info=True)
            yield Response(error=f"❌ Error: {str(e)}")
    
    def _format_error_message(self, status_code: int, response_text: str) -> str:
        """فرمت‌بندی خطای خوانا"""
        try:
            data = json.loads(response_text)
            error_msg = data.get('error', {})
            
            if isinstance(error_msg, dict):
                message = error_msg.get('message', str(error_msg))
                code = error_msg.get('code', '')
                metadata = error_msg.get('metadata', {})
                
                if code:
                    result = f"❌ Error {code}: {message}"
                else:
                    result = f"❌ HTTP {status_code}: {message}"
                
                if metadata:
                    if 'raw' in metadata:
                        result += f"\n\n📋 Details: {metadata['raw'][:200]}"
                
                return result
            
            elif isinstance(error_msg, str):
                return f"❌ HTTP {status_code}: {error_msg}"
            
            else:
                return f"❌ HTTP {status_code}: {response_text[:200]}"
        
        except json.JSONDecodeError:
            return f"❌ HTTP {status_code}: {response_text[:200]}"
    
    def test_connection(self, api_key: str) -> Dict:
        """تست اتصال"""
        try:
            url = self._build_url('test')
            headers = self._build_headers(api_key)
            timeout = self.settings.get('timeout', 10)
            
            # ✅ ساخت payload تست بر اساس پروتکل
            if self.protocol == 'responses':
                payload = {
                    'model': 'gpt-3.5-turbo',
                    'input': 'Hi',
                    'max_output_tokens': 5
                }
            elif self.protocol == 'messages':
                payload = {
                    'model': 'claude-3-haiku-20240307',
                    'messages': [{'role': 'user', 'content': 'Hi'}],
                    'max_tokens': 5
                }
            else:
                payload = {
                    'model': 'gpt-3.5-turbo',
                    'messages': [{'role': 'user', 'content': 'Hi'}],
                    'max_tokens': 5
                }
            
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            
            if resp.status_code == 200:
                return {'success': True, 'message': '✅ Connection successful'}
            else:
                error_msg = self._format_error_message(resp.status_code, resp.text)
                return {'success': False, 'message': error_msg}
        
        except Exception as e:
            return {'success': False, 'message': f'❌ {str(e)}'}


# ============ Provider Factory ============

class ProviderFactory:
    """کارخانه ساخت Provider"""
    
    @staticmethod
    def create_all() -> Dict[str, ProviderAdapter]:
        """ساخت همه Providerها از JSON"""
        providers = KeyManager.get_providers()
        adapters = {}
        
        for p in providers:
            try:
                adapters[p['id']] = ProviderAdapter(p)
            except Exception as e:
                log_error(f"Error creating provider {p.get('id', 'unknown')}: {e}")
        
        log_info(f"Created {len(adapters)} providers")
        return adapters
    
    @staticmethod
    def create(provider_id: str) -> Optional[ProviderAdapter]:
        """ساخت یک Provider"""
        provider_config = KeyManager.get_provider(provider_id)
        if not provider_config:
            return None
        
        try:
            return ProviderAdapter(provider_config)
        except Exception as e:
            log_error(f"Error creating provider {provider_id}: {e}")
            return None