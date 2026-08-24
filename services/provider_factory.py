"""
Provider Factory v5.0 - 9router Only Integration
تمام درخواست‌ها از طریق 9router API هدایت می‌شوند - حذف تمام روش‌های دیگر
"""
import os
import requests
import json
from typing import List, Dict, Optional, AsyncGenerator
from services.key_manager import KeyManager
from utils.logger import log_info, log_error, log_warning

# ✅ 9router Configuration
NINEROUTER_BASE_URL = os.environ.get('NINEROUTER_URL', 'http://localhost:20128')
NINEROUTER_API_KEY = os.environ.get('NINEROUTER_API_KEY', '9router-default-key')


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


# ============ 9router Provider Adapter ============

class NineRouterAdapter:
    """Adapter انحصاری برای 9router - دریافت خودکار همه مدل‌ها از 9router"""
    
    def __init__(self):
        self.id = '9router'
        self.name = '9Router (All Providers)'
        self.type = 'openai_compatible'
        self.base_url = NINEROUTER_BASE_URL.rstrip('/')
        self.settings = {'timeout': 30, 'max_tokens': 4096, 'temperature': 0.7}
        
        # ✅ Mapping prefixهای 9router به نام‌های خوانا
        self.provider_names = {
            'or': 'OpenRouter',
            'cc': 'Claude Code',
            'cx': 'Codex',
            'vertex': 'Vertex AI',
            'glm': 'GLM',
            'minimax': 'MiniMax',
            'kimi': 'Kimi',
            'kr': 'Kiro',
            'oc': 'OpenCode',
            'gh': 'GitHub Copilot',
        }
        
        log_info(f"🔧 Initialized 9router adapter at {self.base_url}")
    
    def _get_headers(self) -> Dict:
        """ساخت headers برای درخواست به 9router"""
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {NINEROUTER_API_KEY}'
        }
    
    def fetch_models(self) -> List[Dict]:
        """✅ دریافت لیست کامل مدل‌ها از 9router API"""
        log_info(f"Fetching all models from 9router...")
        
        try:
            url = f"{self.base_url}/v1/models"
            headers = self._get_headers()
            timeout = self.settings.get('timeout', 30)
            
            resp = requests.get(url, headers=headers, timeout=timeout)
            
            if resp.status_code != 200:
                log_error(f"Failed to fetch models from 9router: HTTP {resp.status_code}")
                log_error(f"Response: {resp.text[:500]}")
                return []
            
            data = resp.json()
            models = []
            
            for m in data.get('data', []):
                model_id = m.get('id', '')
                
                # ✅ استخراج اطلاعات مدل از فرمت 9router
                # فرمت: prefix/model-name (مثلاً or/claude-sonnet-4.5)
                provider_prefix = model_id.split('/')[0] if '/' in model_id else 'unknown'
                provider_name = self.provider_names.get(provider_prefix, provider_prefix.upper())
                
                models.append({
                    'id': model_id,
                    'name': m.get('name', model_id),
                    'provider': provider_name,
                    'provider_prefix': provider_prefix,
                    'is_free': self._is_free_model(model_id, m),
                    'context_window': m.get('context_window', 0),
                    'top_provider': m.get('top_provider', {})
                })
            
            log_info(f"✅ Fetched {len(models)} models from 9router")
            return models
        
        except Exception as e:
            log_error(f"Error fetching models from 9router: {e}", exc_info=True)
            return []
    
    def _is_free_model(self, model_id: str, model_data: Dict) -> bool:
        """بررسی رایگان بودن مدل بر اساس indicators مختلف"""
        # ✅ بررسی بر اساس ID
        free_indicators = [':free', '-free', 'free-', '/free', 'flash', 'mini', 'nano', 'kimi-k2']
        if any(ind in model_id.lower() for ind in free_indicators):
            return True
        
        # ✅ بررسی بر اساس pricing در metadata
        pricing = model_data.get('pricing', {})
        if pricing:
            prompt_price = float(pricing.get('prompt', '0'))
            completion_price = float(pricing.get('completion', '0'))
            if prompt_price == 0 and completion_price == 0:
                return True
        
        # ✅ بررسی top_provider برای free tier
        top_provider = model_data.get('top_provider', {})
        if top_provider.get('is_free', False):
            return True
        
        return False
    
    async def stream_response(self, messages: List[Dict], model: str, api_key: str = None, 
                             custom_url: str = None) -> AsyncGenerator[Response, None]:
        """Stream response از طریق 9router"""
        try:
            # ✅ همیشه از 9router استفاده می‌شود
            url = f"{self.base_url}/v1/chat/completions"
            headers = self._get_headers()
            timeout = self.settings.get('timeout', 30)
            
            # ✅ ساخت payload استاندارد OpenAI-compatible
            payload = {
                'model': model,
                'messages': messages,
                'stream': True,
                'max_tokens': self.settings.get('max_tokens', 4096),
                'temperature': self.settings.get('temperature', 0.7)
            }
            
            log_info(f"📡 Streaming via 9router: {url}")
            log_info(f"🤖 Model: {model}")
            
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
                    
                    # ✅ Parse پاسخ استاندارد OpenAI
                    text = self._parse_stream_response(data)
                    
                    if text:
                        yield Response(text=text)
                
                except json.JSONDecodeError as e:
                    log_warning(f"⚠️ JSON decode error in stream: {e}")
                    continue
        
        except requests.exceptions.Timeout:
            log_error(f"⏱️ Stream timeout")
            yield Response(error="⏱️ Request timeout - please try again")
        
        except requests.exceptions.RequestException as e:
            log_error(f"❌ Stream request error: {e}")
            yield Response(error=f"🌐 Network error: {str(e)}")
        
        except Exception as e:
            log_error(f"❌ Unexpected stream error: {e}", exc_info=True)
            yield Response(error=f"❌ Error: {str(e)}")
    
    def _parse_stream_response(self, data: Dict) -> str:
        """Parse پاسخ stream از 9router (فرمت OpenAI-compatible)"""
        try:
            # ✅ فرمت استاندارد OpenAI
            choices = data.get('choices', [])
            if not choices:
                return ''
            
            delta = choices[0].get('delta', {})
            content = delta.get('content', '')
            
            return content if content else ''
        
        except Exception as e:
            log_warning(f"Error parsing stream response: {e}")
            return ''
    
    def _format_error_message(self, status_code: int, response_text: str) -> str:
        """فرمت‌بندی خطای خوانا"""
        try:
            data = json.loads(response_text)
            error_msg = data.get('error', {})
            
            if isinstance(error_msg, dict):
                message = error_msg.get('message', str(error_msg))
                code = error_msg.get('code', '')
                
                if code:
                    return f"❌ Error {code}: {message}"
                else:
                    return f"❌ HTTP {status_code}: {message}"
            
            elif isinstance(error_msg, str):
                return f"❌ HTTP {status_code}: {error_msg}"
            
            else:
                return f"❌ HTTP {status_code}: {response_text[:200]}"
        
        except json.JSONDecodeError:
            return f"❌ HTTP {status_code}: {response_text[:200]}"
    
    def test_connection(self, api_key: str = None) -> Dict:
        """تست اتصال به 9router"""
        try:
            url = f"{self.base_url}/v1/models"
            headers = self._get_headers()
            timeout = 10
            
            resp = requests.get(url, headers=headers, timeout=timeout)
            
            if resp.status_code == 200:
                return {'success': True, 'message': '✅ 9router connection successful'}
            else:
                return {'success': False, 'message': f'❌ HTTP {resp.status_code}: {resp.text[:200]}'}
        
        except Exception as e:
            return {'success': False, 'message': f'❌ {str(e)}'}
    
    def test_model_health(self, model_id: str, api_key: str = None) -> Dict:
        """بررسی سلامت یک مدل خاص با درخواست تست سبک"""
        try:
            url = f"{self.base_url}/v1/chat/completions"
            headers = self._get_headers()
            timeout = 15  # Timeout برای تست مدل
            
            # ارسال درخواست تست بسیار سبک
            payload = {
                'model': model_id,
                'messages': [{'role': 'user', 'content': '.'}],  # پیام خالی برای تست
                'max_tokens': 1,  # حداقل هزینه
                'stream': False
            }
            
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            
            if resp.status_code == 200:
                return {'success': True, 'message': 'Model is healthy', 'status_code': 200}
            elif resp.status_code == 410:
                return {'success': False, 'message': 'Model has been deprecated (410 Gone)', 'status_code': 410}
            elif resp.status_code == 404:
                return {'success': False, 'message': 'Model not found (404)', 'status_code': 404}
            elif resp.status_code == 401:
                return {'success': False, 'message': 'Unauthorized (401)', 'status_code': 401}
            elif resp.status_code >= 500:
                return {'success': False, 'message': f'Server error ({resp.status_code})', 'status_code': resp.status_code}
            else:
                return {'success': False, 'message': f'HTTP {resp.status_code}: {resp.text[:200]}', 'status_code': resp.status_code}
        
        except requests.exceptions.Timeout:
            return {'success': False, 'message': 'Request timeout', 'status_code': 408}
        except requests.exceptions.ConnectionError as e:
            return {'success': False, 'message': f'Connection error: {str(e)}', 'status_code': 0}
        except Exception as e:
            return {'success': False, 'message': f'Error: {str(e)}', 'status_code': 0}


# ============ Provider Factory ============

class ProviderFactory:
    """کارخانه ساخت Provider - فقط 9router"""
    
    @staticmethod
    def create_all() -> Dict[str, NineRouterAdapter]:
        """ساخت 9router adapter"""
        log_info("Creating 9router adapter...")
        return {'9router': NineRouterAdapter()}
    
    @staticmethod
    def create(provider_id: str) -> Optional[NineRouterAdapter]:
        """ساخت 9router adapter"""
        if provider_id == '9router':
            return NineRouterAdapter()
        log_error(f"Unknown provider: {provider_id}. Only '9router' is supported.")
        return None