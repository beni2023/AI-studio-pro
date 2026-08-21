"""
AI Studio Pro - Main Application v2.0
Dynamic Provider Architecture - Fixed
"""
from flask import Flask, render_template, request, Response, stream_with_context
import json
import re
import os
import time
import atexit
from functools import wraps

from config import CONFIG, MAX_FILE_SIZE, ALLOWED_EXTENSIONS
from services.key_manager import KeyManager
from services.provider_factory import ProviderFactory, ProviderAdapter
from services.context_manager import ContextManager
from services.session_pool import session_pool
from utils.logger import log_info, log_error, log_warning
from utils.validators import validate_api_key, sanitize_text
from werkzeug.utils import secure_filename


# ============ Exception Classes ============

class APIError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


class ValidationError(APIError):
    def __init__(self, message):
        super().__init__(message, 400)


# ============ Flask App ============

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = CONFIG.security.secret_key or 'dev-secret-key'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Providers (Dynamic)
providers_cache = {}


def refresh_providers():
    """به‌روزرسانی cache Providerها"""
    global providers_cache
    providers_cache = ProviderFactory.create_all()
    log_info(f"🔄 Refreshed providers cache: {len(providers_cache)} providers")


# ============ Middleware ============

def handle_api_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except APIError as e:
            log_error(f"API Error: {e}")
            return jresponse({"error": str(e)}, e.status_code)
        except Exception as e:
            log_error(f"Unexpected error: {e}", exc_info=True)
            return jresponse({"error": "Internal server error"}, 500)
    return wrapper


def validate_json_request(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not request.is_json:
            raise ValidationError("Request must be JSON")
        return f(*args, **kwargs)
    return wrapper


@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


# ============ Helper Functions ============

def jresponse(data, status=200):
    return Response(
        json.dumps(data, ensure_ascii=False),
        status=status,
        mimetype="application/json; charset=utf-8"
    )


def clean_custom_url(url: str) -> str:
    if not url:
        return ''
    url = url.strip()
    url = url.replace('\n', '').replace('\r', '').replace('\t', '')
    url = url.rstrip('\\')
    while url.endswith('//'):
        url = url[:-1]
    url = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', url)
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


def validate_custom_url_simple(url: str) -> bool:
    """✅ اضافه شده - اعتبارسنجی URL"""
    if not url:
        return False
    url = clean_custom_url(url)
    if not url.startswith(('http://', 'https://')):
        return False
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if not parsed.netloc:
            return False
        if '.' not in parsed.netloc and parsed.netloc not in ['localhost', '127.0.0.1']:
            return False
        return True
    except Exception as e:
        log_warning(f"URL validation error: {e}")
        return False


# ============ Routes ============

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
@handle_api_errors
def health():
    """بررسی سلامت"""
    results = {}
    for provider_id, adapter in providers_cache.items():
        active_key = KeyManager.get_active_key(provider_id)
        if active_key:
            test_result = adapter.test_connection(active_key['api_key'])
            results[provider_id] = {
                "name": adapter.name,
                "status": "✅ OK" if test_result['success'] else "❌ FAIL",
                "message": test_result['message']
            }
        else:
            results[provider_id] = {
                "name": adapter.name,
                "status": "⚠️ No Key",
                "message": "No active API key"
            }
    
    return jresponse(results)


# ============ Provider Endpoints ============

@app.route("/providers")
@handle_api_errors
def get_providers():
    """دریافت همه Providerها"""
    providers = KeyManager.get_providers()
    
    for p in providers:
        active_key = KeyManager.get_active_key(p['id'])
        p['has_key'] = active_key is not None
        p['key_count'] = len(p.get('keys', []))
        p['model_count'] = len(p.get('models_cache', []))
    
    return jresponse({"providers": providers})


@app.route("/providers/<provider_id>")
@handle_api_errors
def get_provider(provider_id):
    """دریافت یک Provider"""
    provider = KeyManager.get_provider(provider_id)
    if not provider:
        raise APIError("Provider not found", 404)
    return jresponse(provider)

@app.route("/providers/presets")
@handle_api_errors
def get_presets():
    """✅ دریافت preset‌های آماده"""
    presets = KeyManager.get_presets()
    return jresponse({"presets": presets})


@app.route("/providers", methods=["POST"])
@handle_api_errors
@validate_json_request
def add_provider():
    """اضافه کردن Provider"""
    data = request.json or {}
    
    if not data.get('id') or not data.get('name'):
        raise ValidationError("ID and Name are required")
    
    result = KeyManager.add_provider(data)
    
    if result['success']:
        refresh_providers()
    
    return jresponse(result)


@app.route("/providers/<provider_id>", methods=["PUT"])
@handle_api_errors
@validate_json_request
def update_provider(provider_id):
    """به‌روزرسانی Provider"""
    data = request.json or {}
    success = KeyManager.update_provider(provider_id, data)
    
    if success:
        refresh_providers()
    
    return jresponse({"success": success})


@app.route("/providers/<provider_id>", methods=["DELETE"])
@handle_api_errors
def delete_provider(provider_id):
    """حذف Provider"""
    success = KeyManager.delete_provider(provider_id)
    
    if success:
        refresh_providers()
    
    return jresponse({"success": success})


# ============ Key Endpoints ============

@app.route("/providers/<provider_id>/keys")
@handle_api_errors
def get_keys(provider_id):
    """دریافت کلیدهای یک Provider"""
    keys = KeyManager.get_keys(provider_id)
    
    safe_keys = []
    for k in keys:
        safe_key = k.copy()
        if safe_key.get('api_key'):
            key = safe_key['api_key']
            if len(key) > 10:
                safe_key['api_key'] = key[:6] + '••••' + key[-4:]
        safe_keys.append(safe_key)
    
    return jresponse({"keys": safe_keys})


@app.route("/providers/<provider_id>/keys", methods=["POST"])
@handle_api_errors
@validate_json_request
def add_key(provider_id):
    """اضافه کردن کلید"""
    data = request.json or {}
    
    if not data.get('api_key'):
        raise ValidationError("API Key is required")
    
    result = KeyManager.add_key(provider_id, data)
    
    if result['success']:
        refresh_providers()
    
    return jresponse(result)


@app.route("/providers/<provider_id>/keys/<key_id>", methods=["PUT"])
@handle_api_errors
@validate_json_request
def update_key(provider_id, key_id):
    """به‌روزرسانی کلید"""
    data = request.json or {}
    success = KeyManager.update_key(provider_id, key_id, data)
    return jresponse({"success": success})


@app.route("/providers/<provider_id>/keys/<key_id>", methods=["DELETE"])
@handle_api_errors
def delete_key(provider_id, key_id):
    """حذف کلید"""
    success = KeyManager.delete_key(provider_id, key_id)
    
    if success:
        refresh_providers()
    
    return jresponse({"success": success})


@app.route("/providers/<provider_id>/keys/<key_id>/test", methods=["POST"])
@handle_api_errors
def test_key(provider_id, key_id):
    """تست کلید"""
    keys = KeyManager.get_keys(provider_id)
    key = next((k for k in keys if k['id'] == key_id), None)
    
    if not key:
        raise APIError("Key not found", 404)
    
    adapter = providers_cache.get(provider_id)
    if not adapter:
        raise APIError("Provider not found", 404)
    
    result = adapter.test_connection(key['api_key'])
    
    KeyManager.update_key(provider_id, key_id, {
        'last_tested': time.strftime("%Y-%m-%dT%H:%M:%S"),
        'status': 'active' if result['success'] else 'failed'
    })
    
    return jresponse(result)


# ============ Models Endpoints ============

@app.route("/providers/<provider_id>/models")
@handle_api_errors
def get_models(provider_id):
    """دریافت مدل‌ها (از cache یا fetch)"""
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    log_info(f"Getting models for provider: {provider_id}")
    
    if not force_refresh:
        cache = KeyManager.get_models_cache(provider_id)
        if cache:
            log_info(f"Returning {len(cache)} models from cache")
            return jresponse({"models": cache, "from_cache": True})
    
    adapter = providers_cache.get(provider_id)
    if not adapter:
        log_error(f"Provider not found in cache: {provider_id}")
        adapter = ProviderFactory.create(provider_id)
        if not adapter:
            raise APIError(f"Provider not found: {provider_id}", 404)
        providers_cache[provider_id] = adapter
    
    try:
        models = adapter.fetch_models()
        
        if models:
            KeyManager.update_models_cache(provider_id, models)
            log_info(f"✅ Fetched and cached {len(models)} models")
        else:
            log_warning(f"No models returned for {provider_id}")
        
        return jresponse({"models": models, "from_cache": False})
    
    except Exception as e:
        log_error(f"Error fetching models for {provider_id}: {e}", exc_info=True)
        return jresponse({"models": [], "error": str(e)}, 500)


# ============ Streaming Endpoint ============

@app.route("/stream", methods=["POST"])
@handle_api_errors
@validate_json_request
def stream():
    """Stream response با Response class"""
    def generate():
        try:
            data = request.json or {}
            provider_id = data.get("provider")
            api_key = data.get("apiKey")
            model = data.get("model")
            messages = data.get("messages", [])
            custom_url = data.get("customUrl", "")
            
            log_info(f"📥 Stream request: provider={provider_id}, model={model}")
            
            if custom_url:
                custom_url = clean_custom_url(custom_url)
            
            if not provider_id:
                yield f"data: {json.dumps({'error': 'Provider is required'})}\n\n"
                return
            
            if not validate_api_key(api_key):
                yield f"data: {json.dumps({'error': 'Invalid API key'})}\n\n"
                return
            
            if not model:
                yield f"data: {json.dumps({'error': 'Model is required'})}\n\n"
                return
            
            prepared_messages = ContextManager.prepare_context(messages)
            provider = providers_cache.get(provider_id)
            
            if not provider:
                yield f"data: {json.dumps({'error': f'Provider {provider_id} not found'})}\n\n"
                return
            
            log_info(f"🚀 Starting stream")
            
            import asyncio
            
            async def stream_gen():
                async for response in provider.stream_response(
                    prepared_messages, model, api_key, custom_url=custom_url
                ):
                    # ✅ استفاده از to_dict()
                    response_dict = response.to_dict()
                    log_info(f"📤 Yielding: {response_dict}")
                    yield f"data: {json.dumps(response_dict, ensure_ascii=False)}\n\n"
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                gen = stream_gen()
                while True:
                    try:
                        result = loop.run_until_complete(gen.__anext__())
                        yield result
                    except StopAsyncIteration:
                        break
            finally:
                loop.close()
        
        except Exception as e:
            log_error(f"❌ Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype="text/event-stream")


# ============ File Endpoints ============

@app.route("/upload_file", methods=["POST"])
@handle_api_errors
def upload_file():
    """آپلود فایل"""
    if 'file' not in request.files:
        raise ValidationError("No file uploaded")
    
    file = request.files['file']
    
    if file.filename == '':
        raise ValidationError("No file selected")
    
    ext = file.filename.lower().split('.')[-1]
    
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"Unsupported file type: .{ext}")
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    if ext == 'txt':
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = f"[File: {filename}]"
    
    text = sanitize_text(text)
    
    return jresponse({
        "success": True,
        "filename": filename,
        "file_type": ext,
        "text_length": len(text),
        "full_text": text
    })


# ============ Export/Import ============

@app.route("/km/export")
@handle_api_errors
def km_export():
    """Export"""
    keys_json = KeyManager.export_json()
    return Response(
        keys_json,
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=api_keys_export.json"}
    )


@app.route("/km/import", methods=["POST"])
@handle_api_errors
def km_import():
    """Import"""
    if 'file' not in request.files:
        raise ValidationError("No file uploaded")
    
    file = request.files['file']
    content = file.read().decode('utf-8')
    
    success = KeyManager.import_json(content)
    
    if success:
        refresh_providers()
        return jresponse({"success": True, "message": "Imported successfully"})
    else:
        raise ValidationError("Invalid JSON format")


# ============ Error Handlers ============

@app.errorhandler(404)
def not_found(e):
    return jresponse({"error": "Not found"}, 404)


@app.errorhandler(500)
def internal_error(e):
    log_error(f"Internal error: {e}", exc_info=True)
    return jresponse({"error": "Internal server error"}, 500)


# ============ Startup ============

@atexit.register
def cleanup():
    session_pool.close_all()
    log_info("Application shutdown")


def startup_checks():
    log_info("Running startup checks...")
    
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    
    refresh_providers()
    
    log_info("Startup checks completed")


# ============ Main ============

if __name__ == "__main__":
    startup_checks()
    log_info("Starting AI Studio Pro v2.0")
    log_info(f"Environment: {CONFIG.flask_env}")
    log_info(f"Providers loaded: {len(providers_cache)}")
    log_info(f"Server running at http://{CONFIG.host}:{CONFIG.port}")
    app.run(debug=CONFIG.flask_debug, host=CONFIG.host, port=CONFIG.port)