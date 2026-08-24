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
from services.provider_factory import ProviderFactory, NineRouterAdapter
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
    
    return jsonify(results)


@app.route("/api/health/check", methods=["POST"])
@handle_api_errors
def check_model_health():
    """بررسی سلامت یک مدل خاص با استفاده از درخواست تست سبک"""
    data = request.get_json() or {}
    model_id = data.get("model")
    api_key = data.get("api_key")
    provider_id = data.get("provider_id")
    
    if not model_id:
        return jsonify({"error": "Model ID is required"}), 400
    
    if not api_key:
        return jsonify({"error": "API key is required"}), 400
    
    # Try to find the provider adapter
    adapter = None
    if provider_id and provider_id in providers_cache:
        adapter = providers_cache[provider_id]
    else:
        # Default to OpenRouter adapter if no provider specified
        # Try to find a provider that uses openrouter
        for pid, p_adapter in providers_cache.items():
            if 'openrouter' in pid.lower() or 'openrouter' in p_adapter.base_url.lower():
                adapter = p_adapter
                break
    
    if not adapter:
        # Create a temporary OpenRouter-style adapter
        from services.router import RouterAdapter
        adapter = RouterAdapter(
            provider_id="temp_openrouter",
            name="OpenRouter",
            base_url="https://openrouter.ai/api/v1",
            protocol="chat_completions",
            models_endpoint="/models",
            chat_endpoint="/chat/completions"
        )
    
    # Perform lightweight health check
    try:
        test_result = adapter.test_model_health(model_id, api_key)
        
        if test_result.get("success"):
            return jsonify({"status": "healthy", "message": "Model is available"})
        else:
            error_message = test_result.get("message", "")
            status_code = test_result.get("status_code", 500)
            
            # Map error messages to specific statuses
            if "410" in error_message or "gone" in error_message.lower():
                return jsonify({"status": "gone", "message": "Model has been deprecated"}), 410
            elif "404" in error_message or "not found" in error_message.lower():
                return jsonify({"status": "not_found", "message": "Model not found"}), 404
            elif "401" in error_message or "unauthorized" in error_message.lower():
                return jsonify({"status": "auth_error", "message": "Invalid API key"}), 401
            elif status_code >= 500:
                return jsonify({"status": "server_error", "message": "Server error"}), status_code
            else:
                return jsonify({"status": "warning", "message": error_message}), 400
                
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ============ Provider Endpoints ============

@app.route("/providers")
@handle_api_errors
def get_providers():
    """✅ دریافت لیست providerها - فقط 9router"""
    # ✅ همیشه فقط 9router برمی‌گردونه
    return jresponse({
        "providers": [{
            "id": "9router",
            "name": "9Router (All Providers)",
            "icon": "🌐",
            "type": "openai_compatible",
            "has_key": bool(os.environ.get('NINEROUTER_API_KEY')),
            "keys": []
        }]
    })


@app.route("/providers/presets")
@handle_api_errors
def get_presets():
    """✅ دریافت preset‌های آماده (برای سازگاری)"""
    return jresponse({"presets": {}})


@app.route("/providers", methods=["POST"])
@handle_api_errors
@validate_json_request
def add_provider():
    """❌ غیرفعال - فقط 9router پشتیبانی می‌شود"""
    return jresponse({
        "success": False, 
        "error": "Only 9router is supported. All models are automatically fetched from 9router API."
    }, 400)


@app.route("/providers/<provider_id>", methods=["PUT"])
@handle_api_errors
@validate_json_request
def update_provider(provider_id):
    """❌ غیرفعال - فقط 9router پشتیبانی می‌شود"""
    return jresponse({
        "success": False, 
        "error": "Only 9router is supported."
    }, 400)


@app.route("/providers/<provider_id>", methods=["DELETE"])
@handle_api_errors
def delete_provider(provider_id):
    """❌ غیرفعال - فقط 9router پشتیبانی می‌شود"""
    return jresponse({
        "success": False, 
        "error": "Only 9router is supported."
    }, 400)


# ============ Key Endpoints ============
# ✅ حذف شده - 9router از NINEROUTER_API_KEY environment variable استفاده می‌کند

@app.route("/providers/<provider_id>/keys")
@handle_api_errors
def get_keys(provider_id):
    """❌ غیرفعال - فقط 9router پشتیبانی می‌شود"""
    return jresponse({
        "success": False, 
        "error": "Only 9router is supported. API key is configured via NINEROUTER_API_KEY environment variable."
    }, 400)


@app.route("/providers/<provider_id>/keys", methods=["POST"])
@handle_api_errors
@validate_json_request
def add_key(provider_id):
    """❌ غیرفعال - فقط 9router پشتیبانی می‌شود"""
    return jresponse({
        "success": False, 
        "error": "Only 9router is supported."
    }, 400)


@app.route("/providers/<provider_id>/keys/<key_id>", methods=["PUT"])
@handle_api_errors
@validate_json_request
def update_key(provider_id, key_id):
    """❌ غیرفعال - فقط 9router پشتیبانی می‌شود"""
    return jresponse({
        "success": False, 
        "error": "Only 9router is supported."
    }, 400)


@app.route("/providers/<provider_id>/keys/<key_id>", methods=["DELETE"])
@handle_api_errors
def delete_key(provider_id, key_id):
    """❌ غیرفعال - فقط 9router پشتیبانی می‌شود"""
    return jresponse({
        "success": False, 
        "error": "Only 9router is supported."
    }, 400)


@app.route("/providers/<provider_id>/keys/<key_id>/test", methods=["POST"])
@handle_api_errors
def test_key(provider_id, key_id):
    """❌ غیرفعال - فقط 9router پشتیبانی می‌شود"""
    return jresponse({
        "success": False, 
        "error": "Only 9router is supported."
    }, 400)


# ============ Models Endpoints ============

@app.route("/models")
@handle_api_errors
def get_all_models():
    """✅ دریافت همه مدل‌ها از 9router"""
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    log_info("Getting all models from 9router...")
    
    # ✅ استفاده مستقیم از 9router adapter
    adapter = providers_cache.get('9router')
    if not adapter:
        adapter = ProviderFactory.create('9router')
        if not adapter:
            raise APIError("9router adapter not found", 500)
        providers_cache['9router'] = adapter
    
    try:
        models = adapter.fetch_models()
        
        if models:
            log_info(f"✅ Fetched {len(models)} models from 9router")
        else:
            log_warning("No models returned from 9router")
        
        return jresponse({
            "models": models, 
            "from_cache": False,
            "provider": "9router"
        })
    
    except Exception as e:
        log_error(f"Error fetching models from 9router: {e}", exc_info=True)
        return jresponse({"models": [], "error": str(e)}, 500)


@app.route("/providers/<provider_id>/models")
@handle_api_errors
def get_models(provider_id):
    """✅ هدایت به endpoint اصلی /models"""
    # ✅ ریدایرکت به /models برای سازگاری
    return get_all_models()


# ============ Streaming Endpoint ============

@app.route("/stream", methods=["POST"])
@handle_api_errors
@validate_json_request
def stream():
    """Stream response از طریق 9router"""
    def generate():
        try:
            data = request.json or {}
            provider_id = data.get("provider", "9router")  # ✅ پیش‌فرض 9router
            api_key = data.get("apiKey")  # ✅ دیگر استفاده نمی‌شود، از env استفاده می‌شود
            model = data.get("model")
            messages = data.get("messages", [])
            custom_url = data.get("customUrl", "")  # ✅ دیگر استفاده نمی‌شود
            
            log_info(f"📥 Stream request: provider={provider_id}, model={model}")
            
            if not model:
                yield f"data: {json.dumps({'error': 'Model is required'})}\n\n"
                return
            
            prepared_messages = ContextManager.prepare_context(messages)
            
            # ✅ همیشه از 9router استفاده می‌شود
            provider = providers_cache.get('9router')
            if not provider:
                provider = ProviderFactory.create('9router')
                if not provider:
                    yield f"data: {json.dumps({'error': '9router adapter not found'})}\n\n"
                    return
                providers_cache['9router'] = provider
            
            log_info(f"🚀 Starting stream via 9router")
            
            import asyncio
            
            async def stream_gen():
                # ✅ حذف apiKey و custom_url - فقط از 9router استفاده می‌شود
                async for response in provider.stream_response(
                    prepared_messages, model
                ):
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