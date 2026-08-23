// AI Studio Pro - Main Application v2.0
// Dynamic Provider Architecture - Phase 2 Complete
// ✅ باگ‌های streaming، error handling و saveProvider کاملاً اصلاح شد

const state = {
  chatHistory: [], currentChatId: null, allChats: [], lastReq: {},
  isStreaming: false, abortCtrl: null, selectMode: false,
  selectedIndices: new Set(), currentImage: null, uploadedFileData: null,
  currentCommandIndex: 0, searchDebounceTimer: null,
  activeToasts: [], MAX_TOASTS: 4, modelsLoaded: false, assistantIndex: -1,
  COMMANDS: [
    { name: 'New Chat', icon: '✨', shortcut: 'Ctrl+N', action: 'newChat' },
    { name: 'Search', icon: '🔍', shortcut: 'Ctrl+F', action: 'focusSearch' },
    { name: 'Export', icon: '📤', shortcut: 'Ctrl+E', action: 'exportChat' },
    { name: 'Clear Chat', icon: '🗑️', shortcut: 'Ctrl+L', action: 'clearChat' },
    { name: 'Select Mode', icon: '☑️', shortcut: '', action: 'toggleSelectMode' },
    { name: 'Theme Purple', icon: '🟣', shortcut: '', action: 'themePurple' },
    { name: 'Theme Blue', icon: '🔵', shortcut: '', action: 'themeBlue' },
    { name: 'Theme Green', icon: '🟢', shortcut: '', action: 'themeGreen' },
    { name: 'Theme Orange', icon: '🟠', shortcut: '', action: 'themeOrange' },
    { name: 'Scroll Bottom', icon: '⬇️', shortcut: 'End', action: 'scrollBottom' },
    { name: 'Scroll Top', icon: '⬆️', shortcut: 'Home', action: 'scrollTop' },
  ]
};

const utils = {
  escapeHtml(text) { if (!text) return ''; const div = document.createElement('div'); div.textContent = text; return div.innerHTML; },
  checkRTL(el) { if (!el || !el.value) return; const text = el.value; const rtl = (text.match(/[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/g) || []).length; const latin = (text.match(/[a-zA-Z]/g) || []).length; el.classList.toggle('rtl', rtl > latin); },
  isRTL(text) { if (!text) return false; return /[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF]/.test(text); },
  formatMarkdown(text) {
    if (!text) return '';
    let processed = text;
    const codeBlocks = [];
    processed = processed.replace(/```([a-zA-Z0-9_+\-]+)?\n([\s\S]*?)```/g, (match, lang, code) => {
      const idx = codeBlocks.length;
      codeBlocks.push({ lang: lang || 'code', code: code.trim() });
      return '\n__CODEBLOCK_' + idx + '__\n';
    });
    processed = this.escapeHtml(processed);
    processed = processed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    processed = processed.replace(/\n/g, '<br>');
    processed = processed.replace(/__CODEBLOCK_(\d+)__/g, (match, idx) => {
      const block = codeBlocks[parseInt(idx)];
      return `<pre><div class="code-head"><span class="code-lang">${this.escapeHtml(block.lang)}</span><button class="code-copy-btn">📋 Copy</button></div><code class="language-${block.lang}">${this.escapeHtml(block.code)}</code></pre>`;
    });
    return processed;
  },
  async copyToClipboard(text, html = null) {
    if (navigator.clipboard && window.ClipboardItem) {
      try {
        if (html) { await navigator.clipboard.write([new ClipboardItem({ 'text/html': new Blob([html], { type: 'text/html' }), 'text/plain': new Blob([text], { type: 'text/plain' }) })]); return; }
        else { await navigator.clipboard.writeText(text); return; }
      } catch (e) { console.warn('Clipboard API failed:', e); }
    }
    return new Promise((resolve, reject) => {
      try {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.cssText = 'position:fixed;top:0;left:0;width:2em;height:2em;padding:0;border:none;outline:none;box-shadow:none;background:transparent;opacity:0';
        document.body.appendChild(textarea);
        textarea.focus(); textarea.select();
        let success = false;
        try { success = document.execCommand('copy'); } catch (e) { success = false; }
        document.body.removeChild(textarea);
        if (success) resolve(); else reject(new Error('execCommand failed'));
      } catch (e) { reject(e); }
    });
  },
  generateId() { return 'id_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9); },
  truncate(str, length = 30) { if (!str) return ''; return str.length > length ? str.substring(0, length) : str; },
  maskKey(key) { if (!key || key.length < 10) return key || ''; return key.substring(0, 6) + '••••' + key.substring(key.length - 4); }
};

const storage = {
  KEYS: { THEME: 'ai_theme', SIDEBAR_WIDTH: 'ai_sidebar_width', CHATS: 'ai_chats' },
  getTheme() { return localStorage.getItem(this.KEYS.THEME) || 'purple'; },
  saveTheme(theme) { localStorage.setItem(this.KEYS.THEME, theme); },
  getSidebarWidth() { return localStorage.getItem(this.KEYS.SIDEBAR_WIDTH); },
  saveSidebarWidth(width) { localStorage.setItem(this.KEYS.SIDEBAR_WIDTH, width); },
  loadChats() { try { return JSON.parse(localStorage.getItem(this.KEYS.CHATS)) || []; } catch (e) { return []; } },
  saveChats(chats) { try { localStorage.setItem(this.KEYS.CHATS, JSON.stringify(chats)); } catch (e) {} }
};

const api = {
  async getProviders() {
    const res = await fetch('/providers');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  },
  async addProvider(data) {
    const res = await fetch('/providers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  },
  async deleteProvider(providerId) {
    const res = await fetch(`/providers/${providerId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  },
  async addKey(providerId, keyData) {
    const res = await fetch(`/providers/${providerId}/keys`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(keyData)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  },
  async updateKey(providerId, keyId, updateData) {
    const res = await fetch(`/providers/${providerId}/keys/${keyId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updateData)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  },
  async deleteKey(providerId, keyId) {
    const res = await fetch(`/providers/${providerId}/keys/${keyId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  },
  async testKey(providerId, keyId) {
    const res = await fetch(`/providers/${providerId}/keys/${keyId}/test`, { method: 'POST' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  },
  async getModels(providerId, refresh = false) {
    // ✅ همیشه از endpoint /models استفاده می‌کنه که مستقیماً از 9router مدل‌ها رو می‌گیره
    const url = refresh ? `/models?refresh=true` : `/models`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  },
  async streamMessage(payload, signal) {
    const res = await fetch('/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.body;
  },
  async uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/upload_file', { method: 'POST', body: formData });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }
};

const ui = {
  showToast(msg, type = '') {
    showToastEnhanced(msg, type);
  },
  renderMessages() {
    const container = document.getElementById('messages');
    if (state.chatHistory.length === 0) { container.innerHTML = this.getEmptyStateHTML(); document.getElementById('msgCount').textContent = '0 msgs'; return; }
    container.innerHTML = state.chatHistory.map((m, i) => {
      const isUser = m.role === 'user';
      const isChecked = state.selectedIndices.has(i) ? 'checked' : '';
      let imageHtml = '';
      if (m.image) { imageHtml = `<div class="msg-image-container"><img src="${m.image}" alt="Image" class="msg-image" data-action="open-image"><div class="msg-image-actions"><button class="msg-image-btn" data-action="download-image" data-idx="${i}">⬇️</button><button class="msg-image-btn" data-action="copy-image" data-idx="${i}">📋</button></div></div>`; }
      let contentHtml = '';
      if (m.streaming) { 
        contentHtml = ''; 
      } else { 
        const isRtl = utils.isRTL(m.content); 
        contentHtml = `<div class="md ${isRtl ? 'rtl' : ''}">${utils.formatMarkdown(m.content || '')}</div>`; 
      }
      const checkbox = `<input type="checkbox" class="msg-cb" ${isChecked} data-idx="${i}">`;
      let actions = '';
      if (!isUser && m.content && !m.streaming) { actions = `<div class="msg-actions"><button class="msg-action" data-action="copy-msg" data-idx="${i}">📋 Copy</button></div>`; }
      let longMsgClass = ''; let toggleBtn = '';
      if (!isUser && m.content && m.content.length > 1200 && !m.streaming) { longMsgClass = 'long-msg'; toggleBtn = `<button class="toggle-long-btn" data-action="toggle-long">Show more ▼</button>`; }
      return `<div class="msg ${isUser ? 'user' : ''} ${state.selectedIndices.has(i) ? 'selected-msg' : ''}" data-idx="${i}">${checkbox}<div class="avatar">${isUser ? '👤' : '🤖'}</div><div class="bubble ${longMsgClass}">${imageHtml}${contentHtml}${actions}${toggleBtn}</div></div>`;
    }).join('');
    this.addCodeCopyButtons();
    document.getElementById('msgCount').textContent = `${state.chatHistory.length} msgs`;
    container.scrollTop = container.scrollHeight;
  },
  getEmptyStateHTML() { return `<div class="empty"><svg class="empty-icon" viewBox="0 0 120 120" fill="none"><circle cx="60" cy="60" r="50" stroke="url(#grad1)" stroke-width="2" opacity="0.3"/><path d="M40 50 Q60 30 80 50 Q80 70 60 80 Q40 70 40 50" stroke="url(#grad1)" stroke-width="2" fill="none"/><circle cx="50" cy="55" r="3" fill="var(--primary)"/><circle cx="70" cy="55" r="3" fill="var(--secondary)"/><path d="M50 65 Q60 72 70 65" stroke="url(#grad1)" stroke-width="2" fill="none" stroke-linecap="round"/><defs><linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:var(--primary)"/><stop offset="100%" style="stop-color:var(--secondary)"/></linearGradient></defs></svg><h2>Welcome to AI Studio Pro</h2><p>Start a conversation with any AI model</p><div class="chips"><div class="chip" data-chip="Write a Python function">💻 Python</div><div class="chip" data-chip="یه داستان کوتاه بنویس">📖 داستان</div><div class="chip" data-chip="Explain quantum computing">🔬 Explain</div></div></div>`; },
  addCodeCopyButtons() { document.querySelectorAll('.code-copy-btn').forEach(btn => { btn.onclick = (e) => { e.stopPropagation(); const pre = btn.closest('pre'); const code = pre.querySelector('code'); const text = code.innerText; utils.copyToClipboard(text).then(() => { btn.classList.add('copied'); btn.innerHTML = '✓ Copied!'; setTimeout(() => { btn.classList.remove('copied'); btn.innerHTML = '📋 Copy'; }, 2000); ui.showToast('✓ Code copied', 'success'); }).catch(() => ui.showToast('❌ Failed to copy', 'error')); }; }); },
  updateModelInfo(modelName) { document.getElementById('modelInfo').textContent = modelName || 'No model'; },
  updateChatTitle(title) { document.getElementById('chatTitle').textContent = title || 'Untitled'; }
};

// ============ Provider Manager ============

const providerManager = {
  providers: [],
  
  async init() {
    console.log('🚀 Initializing Provider Manager...');
    await this.loadProviders();
    this.renderProviderDropdown();
    this.loadActiveKeyToField();
    
    if (this.providers.length > 0) {
      console.log('📦 Loading models for first provider...');
      await loadModels();
    }
  },
  
  async loadProviders() {
    try {
      const data = await api.getProviders();
      this.providers = data.providers || [];
      this.renderProviderDropdown();
      this.updateKeyCount();
    } catch (e) {
      console.error('❌ Error loading providers:', e);
      ui.showToast('Failed to load providers', 'error');
    }
  },
  
  renderProviderDropdown() {
    const providerSelect = document.getElementById('provider');
    if (!providerSelect) return;
    
    const currentValue = providerSelect.value;
    
    if (this.providers.length === 0) {
      providerSelect.innerHTML = '<option value="">No Providers - Add one first</option>';
      return;
    }
    
    let options = '';
    this.providers.forEach(p => {
      const statusIcon = p.has_key ? '✅' : '⚠️';
      options += `<option value="${p.id}">${p.icon || '🔑'} ${utils.escapeHtml(p.name)} ${statusIcon}</option>`;
    });
    
    providerSelect.innerHTML = options;
    
    if (currentValue && providerSelect.querySelector(`option[value="${currentValue}"]`)) {
      providerSelect.value = currentValue;
    } else if (this.providers.length > 0) {
      providerSelect.value = this.providers[0].id;
    }
    
    updateActiveProviderDisplay();
    updateProviderStatusCard();
  },
  
  getCurrentProvider() {
    const providerId = document.getElementById('provider').value;
    return this.providers.find(p => p.id === providerId);
  },
  
  loadActiveKeyToField() {
    const provider = this.getCurrentProvider();
    if (!provider) return;
    
    const apiKeyField = document.getElementById('apiKey');
    if (!apiKeyField) return;
    
    const activeKey = provider.keys?.find(k => k.is_default && k.enabled) || 
                      provider.keys?.find(k => k.enabled) || 
                      provider.keys?.[0];
    
    if (activeKey && activeKey.api_key) {
      apiKeyField.value = activeKey.api_key;
    } else {
      apiKeyField.value = '';
    }
  },
  
  updateKeyCount() {
    const badge = document.getElementById('kmBadge');
    if (!badge) return;
    
    const totalKeys = this.providers.reduce((sum, p) => sum + (p.keys?.length || 0), 0);
    const readyCount = this.providers.filter(p => p.keys?.length > 0).length;
    const missingCount = this.providers.length - readyCount;
    
    badge.textContent = totalKeys;
    badge.className = 'km-badge ' + (totalKeys > 0 ? 'has-keys' : 'no-keys');
    
    const readyEl = document.getElementById('kmReadyCount');
    const missingEl = document.getElementById('kmMissingCount');
    
    if (readyEl) readyEl.textContent = `${readyCount} ready`;
    if (missingEl) missingEl.textContent = `${missingCount} missing`;
  },
  
  async addProvider(providerData) {
    try {
      const result = await api.addProvider(providerData);
      if (result.success) {
        ui.showToast('Provider added', 'success');
        await this.loadProviders();
        return true;
      } else {
        ui.showToast(result.error || 'Failed', 'error');
        return false;
      }
    } catch (e) {
      console.error('Error adding provider:', e);
      ui.showToast('Failed to add provider', 'error');
      return false;
    }
  },
  
  async deleteProvider(providerId) {
    try {
      const result = await api.deleteProvider(providerId);
      if (result.success) {
        ui.showToast('Provider deleted', 'success');
        await this.loadProviders();
        return true;
      } else {
        ui.showToast('Failed', 'error');
        return false;
      }
    } catch (e) {
      console.error('Error deleting provider:', e);
      ui.showToast('Failed to delete', 'error');
      return false;
    }
  }
};

// ============ Key Manager ============

const keyManager = {
  async addKey(providerId, keyData) {
    try {
      const result = await api.addKey(providerId, keyData);
      if (result.success) {
        ui.showToast('Key added', 'success');
        await providerManager.loadProviders();
        return true;
      } else {
        ui.showToast(result.error || 'Failed', 'error');
        return false;
      }
    } catch (e) {
      console.error('Error adding key:', e);
      ui.showToast('Failed to add key', 'error');
      return false;
    }
  },
  
  async deleteKey(providerId, keyId) {
    try {
      const result = await api.deleteKey(providerId, keyId);
      if (result.success) {
        ui.showToast('Key deleted', 'success');
        await providerManager.loadProviders();
        return true;
      } else {
        ui.showToast('Failed', 'error');
        return false;
      }
    } catch (e) {
      console.error('Error deleting key:', e);
      ui.showToast('Failed to delete', 'error');
      return false;
    }
  },
  
  async testKey(providerId, keyId) {
    try {
      const result = await api.testKey(providerId, keyId);
      return result;
    } catch (e) {
      console.error('Error testing key:', e);
      return { success: false, message: 'Test failed' };
    }
  }
};

// ============ Chat ============

const chat = {
  async sendMessage(textOverride = null) {
    if (state.isStreaming) { ui.showToast('Please wait', 'warning'); return; }
    const input = document.getElementById('prompt');
    const text = textOverride !== null ? textOverride : input.value.trim();
    if (!text && !state.currentImage) { ui.showToast('Enter a message', 'warning'); return; }
    
    const provider = providerManager.getCurrentProvider();
    if (!provider) { ui.showToast('No provider selected', 'warning'); return; }
    
    // ✅ برای 9router نیازی به API key نیست - از environment variable استفاده می‌کنه
    
    const model = document.getElementById('model').value;
    if (!model) { ui.showToast('Select a model', 'warning'); return; }
    
    const messageObj = { role: 'user', content: text || (state.currentImage ? '[Image]' : ''), timestamp: Date.now() };
    if (state.currentImage) messageObj.image = state.currentImage;
    state.chatHistory.push(messageObj);
    if (textOverride === null) { input.value = ''; input.style.height = 'auto'; input.classList.remove('rtl'); }
    if (state.currentImage) this.removeImagePreview();
    if (state.chatHistory.length === 1) ui.updateChatTitle(utils.truncate(text || 'Image'));
    state.lastReq = { provider: provider.id, model };
    state.assistantIndex = state.chatHistory.length;
    state.chatHistory.push({ role: 'assistant', content: '', streaming: true });
    ui.renderMessages();
    state.isStreaming = true;
    
    showStatusIndicator('Thinking...', 'thinking');
    
    const btn = document.getElementById('sendBtn');
    btn.classList.add('stop'); btn.innerHTML = '■'; btn.disabled = false;
    if (state.abortCtrl && !state.abortCtrl.signal.aborted) { try { state.abortCtrl.abort(); } catch (e) {} }
    state.abortCtrl = new AbortController();
    
    let hasError = false;
    
    try {
      showStatusIndicator('Generating...', 'generating');
      
      // ✅ برای 9router نیازی به apiKey نیست - از environment variable استفاده می‌کنه
      const body = await api.streamMessage({ 
        provider: provider.id, 
        model, 
        messages: state.chatHistory.slice(0, -1) 
      }, state.abortCtrl.signal);
      const reader = body.getReader(); const decoder = new TextDecoder();
      let buffer = ''; let fullText = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n'); buffer = lines.pop();
        
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          
          try {
            const rawData = line.slice(6).trim();
            
            if (!rawData || rawData === '[DONE]') {
              continue;
            }
            
            const data = JSON.parse(rawData);
            
            if (data.error) {
              hasError = true;
              fullText += `\n\n❌ ${data.error}`;
              state.chatHistory[state.assistantIndex].content = fullText;
              state.chatHistory[state.assistantIndex].streaming = false;
              ui.renderMessages();
              break;
            }
            
            if (data.done === true) {
              continue;
            }
            
            let extractedText = '';
            
            if (typeof data === 'string') {
              extractedText = data;
            } else if (data.text) {
              extractedText = data.text;
            } else if (data.choices && data.choices[0]) {
              extractedText = data.choices[0].delta?.content || data.choices[0].text || '';
            } else if (data.choices && data.choices[0]?.message) {
              extractedText = data.choices[0].message.content || '';
            } else if (data.response) {
              extractedText = data.response;
            } else {
              continue;
            }
            
            if (extractedText) {
              fullText += extractedText;
              state.chatHistory[state.assistantIndex].content = fullText;
              this.updateStreamingMessage(fullText);
            }
            
          } catch (e) {
            console.error('❌ Parse error:', e, 'Line:', line);
          }
        }
        
        if (hasError) break;
      }
      
      if (!hasError) {
        state.chatHistory[state.assistantIndex].streaming = false;
        ui.renderMessages();
      }
      
    } catch (e) {
      state.chatHistory[state.assistantIndex].streaming = false;
      
      if (e.name === 'AbortError') {
        state.chatHistory[state.assistantIndex].content += '\n\n*[Stopped]*';
      } else {
        state.chatHistory[state.assistantIndex].content = '❌ Network Error: ' + e.message;
      }
      ui.renderMessages();
      
    } finally {
      state.isStreaming = false; 
      state.assistantIndex = -1;
      btn.classList.remove('stop'); 
      btn.innerHTML = '➤'; 
      btn.disabled = false;
      document.getElementById('msgCount').textContent = `${state.chatHistory.length} msgs`;
      
      if (!hasError) {
        showStatusIndicator('Done', 'done');
        setTimeout(hideStatusIndicator, 2000);
      }
      
      this.saveCurrentChat();
    }
  },
  updateStreamingMessage(text) {
    const container = document.getElementById('messages');
    const msgs = container.querySelectorAll('.msg');
    const lastMsg = msgs[state.assistantIndex];
    if (!lastMsg) return;
    const bubble = lastMsg.querySelector('.bubble');
    if (!bubble) return;
    let streamEl = bubble.querySelector('.streaming-text');
    if (!streamEl) {
      const isRtl = utils.isRTL(text);
      streamEl = document.createElement('div');
      streamEl.className = `streaming-text ${isRtl ? 'rtl' : ''}`;
      bubble.appendChild(streamEl);
    }
    streamEl.textContent = text;
    container.scrollTop = container.scrollHeight;
  },
  removeImagePreview() { state.currentImage = null; const container = document.getElementById('imagePreviewContainer'); container.innerHTML = ''; container.hidden = true; },
  saveCurrentChat() {
    if (state.chatHistory.length === 0) return;
    const title = state.chatHistory.find(m => m.role === 'user')?.content?.substring(0, 30) || 'Untitled';
    const provider = providerManager.getCurrentProvider();
    const model = document.getElementById('model').value;
    const chatData = { id: state.currentChatId || utils.generateId(), title, messages: state.chatHistory, provider: provider?.id, model, updatedAt: Date.now() };
    const idx = state.allChats.findIndex(c => c.id === chatData.id);
    if (idx >= 0) state.allChats[idx] = chatData; else state.allChats.unshift(chatData);
    state.currentChatId = chatData.id;
    storage.saveChats(state.allChats);
    this.renderChatList();
  },
  renderChatList() {
    const list = document.getElementById('chatHistoryList');
    if (state.allChats.length === 0) { list.innerHTML = '<div style="color:var(--text-muted); font-size:0.75rem; text-align:center; padding:8px;">No saved chats</div>'; return; }
    list.innerHTML = state.allChats.map(c => `<div class="chat-history-item ${c.id === state.currentChatId ? 'active' : ''}" data-chat-id="${c.id}"><div class="chat-history-title">${utils.escapeHtml(c.title || 'Untitled')}</div><div class="chat-history-meta"><span>${c.messages.length} msgs • ${c.provider || ''}</span><button data-action="delete-chat" data-chat-id="${c.id}" style="background:none; border:none; color:var(--danger); cursor:pointer;">🗑️</button></div></div>`).join('');
  }
};

// ============ Models ============

async function loadModels() {
  const provider = providerManager.getCurrentProvider();
  if (!provider) return;
  
  const sel = document.getElementById('model');
  sel.innerHTML = '<option class="skeleton" disabled>Loading...</option>';
  state.modelsLoaded = false;
  
  try {
    const data = await api.getModels(provider.id);
    const models = data.models || [];
    
    if (models.length > 0) {
      sel.innerHTML = models.map(m => {
        const badge = m.is_free ? '<span class="model-free-badge">FREE</span>' : '<span class="model-paid-badge">PAID</span>';
        return `<option value="${utils.escapeHtml(m.id)}">${utils.escapeHtml(m.name)} ${badge}</option>`;
      }).join('');
      state.modelsLoaded = true;
      ui.updateModelInfo(sel.value);
      updateActiveModelDisplay();
      updateProviderStatusCard();
    } else {
      sel.innerHTML = '<option value="" disabled>⚠️ No models - Add API key first</option>';
      ui.showToast('No models available', 'warning');
    }
  } catch (e) {
    console.error('❌ Error loading models:', e);
    sel.innerHTML = '<option value="" disabled>⚠️ Failed to load models</option>';
    ui.updateModelInfo('No model');
    ui.showToast('Failed to load models', 'error');
  }
}

async function forceRefreshModels() {
  const provider = providerManager.getCurrentProvider();
  if (!provider) {
    ui.showToast('No provider selected', 'warning');
    return;
  }
  
  ui.showToast('Refreshing models...', 'info');
  
  const sel = document.getElementById('model');
  sel.innerHTML = '<option class="skeleton" disabled>Loading...</option>';
  state.modelsLoaded = false;
  
  try {
    const data = await api.getModels(provider.id, true);
    const models = data.models || [];
    
    if (models.length > 0) {
      sel.innerHTML = models.map(m => {
        const badge = m.is_free ? '<span class="model-free-badge">FREE</span>' : '<span class="model-paid-badge">PAID</span>';
        return `<option value="${utils.escapeHtml(m.id)}">${utils.escapeHtml(m.name)} ${badge}</option>`;
      }).join('');
      state.modelsLoaded = true;
      ui.updateModelInfo(sel.value);
      updateActiveModelDisplay();
      updateProviderStatusCard();
      ui.showToast(`Loaded ${models.length} models`, 'success');
    } else {
      sel.innerHTML = '<option value="" disabled>⚠️ No models available</option>';
      ui.showToast('No models available', 'warning');
    }
  } catch (e) {
    console.error('Error refreshing models:', e);
    sel.innerHTML = '<option value="" disabled>⚠️ Failed to load models</option>';
    ui.updateModelInfo('No model');
    ui.showToast('Failed to refresh models', 'error');
  }
}

// ============ Status Indicator ============

function showStatusIndicator(message, type = 'thinking') {
  const container = document.getElementById('messages');
  const msgs = container.querySelectorAll('.msg');
  const lastMsg = msgs[state.assistantIndex];
  
  if (!lastMsg) return;
  
  const bubble = lastMsg.querySelector('.bubble');
  if (!bubble) return;
  
  const existing = bubble.querySelector('.status-indicator');
  if (existing) existing.remove();
  
  const indicator = document.createElement('div');
  indicator.className = `status-indicator ${type}`;
  
  if (type === 'thinking' || type === 'generating') {
    indicator.innerHTML = `<div class="status-dots"><span></span><span></span><span></span></div><span class="status-text">${message}</span>`;
  } else if (type === 'done') {
    indicator.innerHTML = `<span class="status-icon">✓</span><span class="status-text">${message}</span>`;
  } else if (type === 'error') {
    indicator.innerHTML = `<span class="status-icon">✕</span><span class="status-text">${message}</span>`;
  }
  
  bubble.appendChild(indicator);
  container.scrollTop = container.scrollHeight;
}

function hideStatusIndicator() {
  const container = document.getElementById('messages');
  const msgs = container.querySelectorAll('.msg');
  const lastMsg = msgs[state.assistantIndex];
  if (!lastMsg) return;
  
  const bubble = lastMsg.querySelector('.bubble');
  if (!bubble) return;
  
  const indicator = bubble.querySelector('.status-indicator');
  if (indicator) {
    indicator.classList.add('fade-out');
    setTimeout(() => { if (indicator.parentNode) indicator.remove(); }, 300);
  }
}

// ============ Token Counter & Active Displays ============

function updateTokenCounter() {
  const prompt = document.getElementById('prompt');
  const counter = document.getElementById('tokenCounter');
  if (!prompt || !counter) return;
  
  const text = prompt.value;
  const estimatedTokens = Math.ceil(text.length / 4);
  counter.textContent = `${estimatedTokens} tokens`;
  
  counter.classList.remove('warning', 'danger');
  if (estimatedTokens > 3000) counter.classList.add('danger');
  else if (estimatedTokens > 2000) counter.classList.add('warning');
}

function updateActiveModelDisplay() {
  const modelSelect = document.getElementById('model');
  const display = document.getElementById('activeModelDisplay');
  if (!modelSelect || !display) return;
  
  const selectedOption = modelSelect.options[modelSelect.selectedIndex];
  display.textContent = (selectedOption && selectedOption.value) ? selectedOption.text.split(' ')[0] : 'No model';
}

function updateActiveProviderDisplay() {
  const providerSelect = document.getElementById('provider');
  const display = document.getElementById('activeProviderDisplay');
  if (!providerSelect || !display) return;
  
  const selectedOption = providerSelect.options[providerSelect.selectedIndex];
  display.textContent = (selectedOption && selectedOption.value) ? selectedOption.text.split(' ')[0] : 'No provider';
}

function updateProviderStatusCard() {
  const provider = providerManager.getCurrentProvider();
  const card = document.getElementById('providerStatusCard');
  if (!card) return;
  
  if (!provider) {
    card.style.display = 'none';
    return;
  }
  
  card.style.display = 'block';
  document.getElementById('providerStatusIcon').textContent = provider.icon || '🔑';
  document.getElementById('providerStatusName').textContent = provider.name;
  
  const statusDot = document.getElementById('providerStatusDot');
  const statusText = document.getElementById('providerStatusText');
  
  if (provider.keys && provider.keys.length > 0) {
    statusDot.className = 'status-dot connected';
    statusText.textContent = 'Connected';
  } else {
    statusDot.className = 'status-dot disconnected';
    statusText.textContent = 'No Key';
  }
  
  document.getElementById('providerKeyCount').textContent = `${provider.keys?.length || 0} keys`;
  document.getElementById('providerModelCount').textContent = `${provider.models_cache?.length || 0} models`;
}

// ============ Enhanced Toast ============

function showToastEnhanced(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  while (state.activeToasts.length >= state.MAX_TOASTS) {
    const oldest = state.activeToasts.shift();
    if (oldest && oldest.parentNode) oldest.remove();
  }
  
  const toastEl = document.createElement('div');
  toastEl.className = `toast ${type}`;
  const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
  
  toastEl.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ️'}</span><span class="toast-content">${message}</span><button class="toast-close" onclick="this.parentElement.remove()">✕</button>`;
  
  container.appendChild(toastEl);
  state.activeToasts.push(toastEl);
  
  setTimeout(() => toastEl.classList.add('show'), 10);
  setTimeout(() => {
    toastEl.classList.remove('show');
    setTimeout(() => {
      if (toastEl.parentNode) toastEl.remove();
      const idx = state.activeToasts.indexOf(toastEl);
      if (idx > -1) state.activeToasts.splice(idx, 1);
    }, 300);
  }, 3000);
}

// ============ Preset Data & Apply ============

const providerPresets = {
  openrouter: { name: 'OpenRouter', icon: '🌐', protocol: 'chat_completions', base_url: 'https://openrouter.ai/api/v1', models_endpoint: '/models', chat_endpoint: '/chat/completions' },
  openmodel: { name: 'OpenModel', icon: '🤖', protocol: 'responses', base_url: 'https://api.openmodel.ai', models_endpoint: '/v1/models', chat_endpoint: '/v1/responses' },
  anthropic: { name: 'Anthropic', icon: '🎭', protocol: 'messages', base_url: 'https://api.anthropic.com', models_endpoint: '/v1/models', chat_endpoint: '/v1/messages' },
  gemini: { name: 'Google Gemini', icon: '💎', protocol: 'gemini', base_url: 'https://generativelanguage.googleapis.com', models_endpoint: '/v1beta/models', chat_endpoint: '/v1beta/models/{model}:generateContent' },
  openai: { name: 'OpenAI', icon: '🧠', protocol: 'chat_completions', base_url: 'https://api.openai.com/v1', models_endpoint: '/models', chat_endpoint: '/chat/completions' }
};

function applyPreset(presetKey) {
  if (!presetKey) return;
  const preset = providerPresets[presetKey];
  if (!preset) return;
  
  console.log('🎨 Applying preset:', presetKey);
  
  const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };
  
  setVal('apId', presetKey);
  setVal('apName', preset.name);
  setVal('apIcon', preset.icon);
  setVal('apProtocol', preset.protocol);
  setVal('apBaseUrl', preset.base_url);
  setVal('apModelsEndpoint', preset.models_endpoint);
  setVal('apChatEndpoint', preset.chat_endpoint);
  
  ui.showToast(`✓ Preset applied: ${preset.name}`, 'success');
}

// ============ Save Provider (Clean & Safe) ============

async function saveProvider() {
  try {
    const getVal = (id, fallback = '') => { const el = document.getElementById(id); return el ? el.value.trim() : fallback; };
    
    const rawId = getVal('apId');
    const providerId = rawId.toLowerCase().replace(/\s+/g, '-');
    const name = getVal('apName');
    const icon = getVal('apIcon') || '🔑';
    const protocol = getVal('apProtocol') || 'chat_completions';
    const baseUrl = getVal('apBaseUrl');
    const modelsEndpoint = getVal('apModelsEndpoint') || '/models';
    const chatEndpoint = getVal('apChatEndpoint') || '/chat/completions';

    if (!providerId || !name || !baseUrl) {
      ui.showToast('ID, Name, and Base URL are required', 'warning');
      return;
    }

    if (!baseUrl.startsWith('http://') && !baseUrl.startsWith('https://')) {
      ui.showToast('Base URL must start with http:// or https://', 'warning');
      return;
    }

    const providerData = {
      id: providerId,
      name: name,
      icon: icon,
      type: 'openai_compatible',
      protocol: protocol,
      base_url: baseUrl,
      endpoints: { models: modelsEndpoint, chat: chatEndpoint, test: chatEndpoint }
    };

    console.log('💾 Saving provider:', providerData);
    const success = await providerManager.addProvider(providerData);
    
    if (success) {
      const modal = document.getElementById('addProviderModal');
      if (modal) modal.hidden = true;
      
      ['apId', 'apName', 'apIcon', 'apBaseUrl', 'apModelsEndpoint', 'apChatEndpoint'].forEach(id => {
        const el = document.getElementById(id); if (el) el.value = '';
      });
      const pEl = document.getElementById('apProtocol'); if (pEl) pEl.value = 'chat_completions';
      const prEl = document.getElementById('apPreset'); if (prEl) prEl.value = '';
      
      renderKeyManagerUI();
      
      const providerSelect = document.getElementById('provider');
      if (providerSelect) {
        providerSelect.value = providerData.id;
        providerManager.loadActiveKeyToField();
        await loadModels();
      }
    }
  } catch (error) {
    console.error('❌ saveProvider error:', error);
    ui.showToast('Error saving provider: ' + error.message, 'error');
  }
}

// ============ Initialize ============

document.addEventListener('DOMContentLoaded', () => {
  console.log('✅ AI Studio Pro v2.0 initialized');
  initTheme(); initSidebar(); initChats(); initEventListeners(); initResizeHandle(); initDragAndDrop();
  providerManager.init();
  keyboard.init({ openCommandPalette, newChat, focusSearch, exportChat, clearChat, closeOverlays, renderCommands, executeCommand });
});

function initTheme() { const theme = storage.getTheme(); applyTheme(theme, false); document.querySelectorAll('.theme-dot').forEach(dot => { dot.addEventListener('click', () => applyTheme(dot.dataset.theme, true)); }); }
function applyTheme(theme, save = true) { document.documentElement.setAttribute('data-theme', theme); document.querySelectorAll('.theme-dot').forEach(d => d.classList.remove('active')); const activeDot = document.querySelector(`.theme-dot.${theme}`); if (activeDot) activeDot.classList.add('active'); if (save) { storage.saveTheme(theme); ui.showToast(`Theme: ${theme}`, 'info'); } }
function initSidebar() { const width = storage.getSidebarWidth(); if (width) { document.documentElement.style.setProperty('--sidebar-width', width + 'px'); document.getElementById('inputArea').style.left = width + 'px'; } }
function initResizeHandle() { const handle = document.getElementById('resizeHandle'); const sidebar = document.getElementById('sidebar'); let isResizing = false; handle.addEventListener('mousedown', (e) => { isResizing = true; handle.classList.add('active'); document.body.style.cursor = 'col-resize'; document.body.style.userSelect = 'none'; }); document.addEventListener('mousemove', (e) => { if (!isResizing) return; const newWidth = Math.max(250, Math.min(500, e.clientX)); sidebar.style.width = newWidth + 'px'; document.documentElement.style.setProperty('--sidebar-width', newWidth + 'px'); document.getElementById('inputArea').style.left = newWidth + 'px'; }); document.addEventListener('mouseup', () => { if (isResizing) { isResizing = false; handle.classList.remove('active'); document.body.style.cursor = ''; document.body.style.userSelect = ''; const width = sidebar.style.width; if (width) storage.saveSidebarWidth(parseInt(width)); } }); }
function initChats() { state.allChats = storage.loadChats(); chat.renderChatList(); }

function initDragAndDrop() { const overlay = document.getElementById('dragOverlay'); let dragCounter = 0; document.addEventListener('dragenter', (e) => { e.preventDefault(); dragCounter++; if (e.dataTransfer.types.includes('Files')) overlay.hidden = false; }); document.addEventListener('dragleave', (e) => { e.preventDefault(); dragCounter--; if (dragCounter === 0) overlay.hidden = true; }); document.addEventListener('dragover', (e) => e.preventDefault()); document.addEventListener('drop', (e) => { e.preventDefault(); dragCounter = 0; overlay.hidden = true; const files = e.dataTransfer.files; if (files.length > 0) { const file = files[0]; if (file.type.startsWith('image/')) handleImageFile(file); else ui.showToast('Drop an image', 'warning'); } }); }
function handleImageFile(file) { if (!file.type.startsWith('image/')) { ui.showToast('Image file only', 'warning'); return; } if (file.size > 10 * 1024 * 1024) { ui.showToast('Max 10MB', 'warning'); return; } const reader = new FileReader(); reader.onload = (e) => { state.currentImage = e.target.result; showImagePreview(state.currentImage); }; reader.readAsDataURL(file); }
function showImagePreview(imageData) { const container = document.getElementById('imagePreviewContainer'); container.innerHTML = `<div class="image-preview"><img src="${imageData}" alt="Preview"><button class="image-preview-remove" id="removeImageBtn">✕</button></div>`; container.hidden = false; document.getElementById('removeImageBtn').addEventListener('click', () => chat.removeImagePreview()); }

function initEventListeners() {
  document.getElementById('provider').addEventListener('change', () => { loadModels(); providerManager.loadActiveKeyToField(); });
  document.getElementById('model').addEventListener('change', (e) => { ui.updateModelInfo(e.target.value); updateActiveModelDisplay(); });
  document.getElementById('sendBtn').addEventListener('click', () => chat.sendMessage());
  
  const prompt = document.getElementById('prompt');
  prompt.addEventListener('input', function() { 
    this.style.height = 'auto'; 
    this.style.height = Math.min(this.scrollHeight, 200) + 'px'; 
    utils.checkRTL(this);
    updateTokenCounter();
  });
  prompt.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); chat.sendMessage(); } });
  
  document.getElementById('attachBtn').addEventListener('click', () => document.getElementById('imageInput').click());
  document.getElementById('imageInput').addEventListener('change', (e) => { const file = e.target.files[0]; if (file) handleImageFile(file); e.target.value = ''; });
  document.getElementById('newChatBtn').addEventListener('click', newChat);
  document.getElementById('clearAllChatsBtn').addEventListener('click', () => { if (state.allChats.length === 0) { ui.showToast('No chats', 'warning'); return; } if (!confirm('Delete ALL?')) return; state.allChats = []; state.chatHistory = []; state.currentChatId = null; state.selectedIndices.clear(); document.getElementById('copyFab').hidden = true; ui.updateChatTitle('Untitled'); storage.saveChats(state.allChats); ui.renderMessages(); chat.renderChatList(); ui.showToast('All cleared', 'success'); });
  document.getElementById('clearChatBtn').addEventListener('click', clearChat);
  document.getElementById('exportChatBtn').addEventListener('click', exportChat);
  document.getElementById('commandPaletteBtn').addEventListener('click', openCommandPalette);
  document.getElementById('selectBtn').addEventListener('click', toggleSelectMode);
  document.getElementById('copyFab').addEventListener('click', copySelected);
  document.getElementById('copyAllBtn').addEventListener('click', (e) => { e.stopPropagation(); document.getElementById('copyMenu').hidden = !document.getElementById('copyMenu').hidden; });
  document.querySelectorAll('.dropdown-item').forEach(item => { item.addEventListener('click', () => { copyAll(item.dataset.format); document.getElementById('copyMenu').hidden = true; }); });
  document.addEventListener('click', (e) => { if (!e.target.closest('.dropdown')) document.getElementById('copyMenu').hidden = true; if (!e.target.closest('.context-menu')) document.getElementById('contextMenu').hidden = true; });
  document.getElementById('closeModalBtn').addEventListener('click', () => document.getElementById('copyModal').hidden = true);
  document.getElementById('copyFromModalBtn').addEventListener('click', async () => { const txt = document.getElementById('modalContent').value; try { await utils.copyToClipboard(txt); ui.showToast('Copied', 'success'); document.getElementById('copyModal').hidden = true; } catch (e) { ui.showToast('Copy failed', 'error'); } });
  document.getElementById('fileUploadArea').addEventListener('click', () => document.getElementById('fileInput').click());
  document.getElementById('fileInput').addEventListener('change', (e) => { const file = e.target.files[0]; if (file) handleFile(file); });
  
  const searchInput = document.getElementById('searchInput');
  searchInput.addEventListener('input', function() { clearTimeout(state.searchDebounceTimer); state.searchDebounceTimer = setTimeout(() => handleSearch(this.value), 300); });
  document.getElementById('searchClearBtn').addEventListener('click', () => { searchInput.value = ''; document.getElementById('searchResults').innerHTML = ''; document.getElementById('searchClearBtn').style.display = 'none'; searchInput.focus(); });
  
  document.getElementById('messages').addEventListener('click', handleMessageClick);
  document.getElementById('messages').addEventListener('contextmenu', handleContextMenu);
  document.getElementById('chatHistoryList').addEventListener('click', handleChatListClick);
  
  const refreshModelsBtn = document.getElementById('refreshModelsBtn');
  if (refreshModelsBtn) refreshModelsBtn.addEventListener('click', forceRefreshModels);
  
  document.getElementById('openKeyManagerBtn').addEventListener('click', () => { 
    document.getElementById('keyManagerModal').hidden = false; 
    renderKeyManagerUI(); 
  });
  document.getElementById('closeKeyManagerBtn').addEventListener('click', () => { 
    document.getElementById('keyManagerModal').hidden = true; 
  });
  document.getElementById('kmAddKeyBtn').addEventListener('click', () => {
    ui.showToast('9Router API key is configured via NINEROUTER_API_KEY environment variable', 'info');
  });
}

function renderKeyManagerUI() {
  const container = document.getElementById('kmKeysList');
  if (!container) return;
  
  // ✅ نمایش پیام ساده - فقط 9router پشتیبانی می‌شود
  container.innerHTML = '<div class="empty-keys"><div class="empty-keys-icon">🌐</div><div>9Router is the only provider</div><div style="font-size:0.8rem; margin-top:8px;">All models are automatically fetched from 9Router API.</div><div style="font-size:0.75rem; margin-top:4px; color:var(--text-muted);">Make sure NINEROUTER_API_KEY is set in your .env file.</div></div>';
}

// ✅ توابع حذف شده - 9Router از environment variable استفاده می‌کند
async function testKeyFromUI(providerId, keyId) {
  ui.showToast('9Router API key is configured via environment variable. Check NINEROUTER_API_KEY in your .env file.', 'info');
}

async function deleteKeyFromUI(providerId, keyId) {
  ui.showToast('Cannot delete keys - 9Router uses environment variable NINEROUTER_API_KEY', 'warning');
}

async function deleteProviderFromUI(providerId) {
  ui.showToast('Cannot delete 9Router - it is the only supported provider', 'warning');
}

function handleMessageClick(e) { const target = e.target; if (target.classList.contains('chip')) { const text = target.dataset.chip; const prompt = document.getElementById('prompt'); prompt.value = text; utils.checkRTL(prompt); prompt.focus(); return; } if (target.classList.contains('msg-cb')) { const idx = parseInt(target.dataset.idx); if (target.checked) state.selectedIndices.add(idx); else state.selectedIndices.delete(idx); updateSelectUI(); return; } const action = target.dataset.action; const idx = parseInt(target.dataset.idx); if (action === 'copy-msg') { const msg = state.chatHistory[idx]; utils.copyToClipboard(msg.content).then(() => ui.showToast('Copied', 'success')).catch(() => ui.showToast('Copy failed', 'error')); } else if (action === 'toggle-long') { const bubble = target.closest('.bubble'); bubble.classList.toggle('expanded'); target.textContent = bubble.classList.contains('expanded') ? 'Show less ▲' : 'Show more ▼'; } else if (action === 'download-image') { const msg = state.chatHistory[idx]; const link = document.createElement('a'); link.href = msg.image; link.download = `image-${idx}.png`; link.click(); ui.showToast('Downloaded', 'success'); } else if (action === 'copy-image') { const msg = state.chatHistory[idx]; fetch(msg.image).then(res => res.blob()).then(blob => navigator.clipboard.write([new ClipboardItem({ [blob.type]: blob })])).then(() => ui.showToast('Copied', 'success')).catch(() => ui.showToast('Failed', 'error')); } else if (action === 'open-image') { window.open(target.src, '_blank'); } }
function handleContextMenu(e) { const msg = e.target.closest('.msg'); if (!msg) return; e.preventDefault(); const idx = parseInt(msg.dataset.idx); const message = state.chatHistory[idx]; const items = [{ icon: '📋', label: 'Copy', action: `copy-msg-${idx}` }, { icon: '✏️', label: 'Edit', action: `edit-msg-${idx}` }]; if (message.role === 'assistant' && idx === state.chatHistory.length - 1) items.push({ icon: '🔄', label: 'Regenerate', action: 'regen-last' }); items.push({ icon: '🗑️', label: 'Delete', action: `delete-msg-${idx}`, danger: true }); const menu = document.getElementById('contextMenu'); menu.innerHTML = items.map(item => `<button class="context-menu-item ${item.danger ? 'danger' : ''}" data-context-action="${item.action}">${item.icon} ${item.label}</button>`).join(''); const menuWidth = 200; const menuHeight = items.length * 40; const maxX = window.innerWidth - menuWidth - 10; const maxY = window.innerHeight - menuHeight - 10; menu.style.left = Math.max(10, Math.min(e.clientX, maxX)) + 'px'; menu.style.top = Math.max(10, Math.min(e.clientY, maxY)) + 'px'; menu.hidden = false; menu.querySelectorAll('.context-menu-item').forEach(item => { item.onclick = () => { handleContextAction(item.dataset.contextAction, idx); menu.hidden = true; }; }); }
function handleContextAction(action, idx) { if (action === `copy-msg-${idx}`) { utils.copyToClipboard(state.chatHistory[idx].content).then(() => ui.showToast('Copied', 'success')).catch(() => ui.showToast('Failed', 'error')); } else if (action === `edit-msg-${idx}`) { const newText = prompt('Edit:', state.chatHistory[idx].content); if (newText !== null && newText.trim()) { state.chatHistory[idx].content = newText.trim(); ui.renderMessages(); ui.showToast('Edited', 'success'); } } else if (action === `delete-msg-${idx}`) { if (!confirm('Delete?')) return; state.chatHistory.splice(idx, 1); ui.renderMessages(); ui.showToast('Deleted', 'info'); } else if (action === 'regen-last') { regenLast(); } }
function handleChatListClick(e) { const deleteBtn = e.target.closest('[data-action="delete-chat"]'); if (deleteBtn) { e.stopPropagation(); const chatId = deleteBtn.dataset.chatId; if (!confirm('Delete?')) return; state.allChats = state.allChats.filter(c => c.id !== chatId); if (state.currentChatId === chatId) { state.chatHistory = []; state.currentChatId = null; state.selectedIndices.clear(); document.getElementById('copyFab').hidden = true; ui.updateChatTitle('Untitled'); ui.renderMessages(); } storage.saveChats(state.allChats); chat.renderChatList(); ui.showToast('Deleted', 'info'); return; } const item = e.target.closest('.chat-history-item'); if (item) openChat(item.dataset.chatId); }

function newChat() { if (state.chatHistory.length > 0) chat.saveCurrentChat(); state.chatHistory = []; state.currentChatId = null; state.lastReq = {}; state.selectedIndices.clear(); state.assistantIndex = -1; document.getElementById('copyFab').hidden = true; ui.updateChatTitle('Untitled'); ui.renderMessages(); chat.renderChatList(); ui.showToast('New chat', 'info'); }
function clearChat() { if (!confirm('Clear?')) return; state.chatHistory = []; state.lastReq = {}; state.selectedIndices.clear(); state.assistantIndex = -1; document.getElementById('copyFab').hidden = true; ui.updateChatTitle('Untitled'); ui.renderMessages(); ui.showToast('Cleared', 'info'); }

function openChat(id) {
  const chatData = state.allChats.find(c => c.id === id);
  if (!chatData) return;
  if (state.chatHistory.length > 0 && state.currentChatId !== id) chat.saveCurrentChat();
  state.chatHistory = chatData.messages;
  state.currentChatId = id;
  state.selectedIndices.clear();
  document.getElementById('copyFab').hidden = true;
  
  const providerId = chatData.provider;
  const model = chatData.model || '';
  
  if (providerId) document.getElementById('provider').value = providerId;
  
  loadModels().then(() => {
    if (model) {
      const modelSelect = document.getElementById('model');
      let found = false;
      for (let i = 0; i < modelSelect.options.length; i++) {
        if (modelSelect.options[i].value === model) { modelSelect.selectedIndex = i; found = true; break; }
      }
      if (!found && modelSelect.options.length > 0) modelSelect.selectedIndex = 0;
    }
    providerManager.loadActiveKeyToField();
    ui.updateChatTitle(chatData.title);
    ui.updateModelInfo(model || 'No model');
    ui.renderMessages();
    chat.renderChatList();
    ui.showToast(`Loaded`, 'info');
  });
}

async function exportChat() { if (state.chatHistory.length === 0) { ui.showToast('No messages', 'error'); return; } let md = `# ${document.getElementById('chatTitle').textContent}\n\n**Date:** ${new Date().toLocaleString()}\n\n**Model:** ${state.lastReq.model || 'Unknown'}\n\n---\n\n`; state.chatHistory.forEach(m => { if (m.image) md += `### ${m.role === 'user' ? 'User' : 'AI'} (with image)\n${m.content}\n\n`; else md += `### ${m.role === 'user' ? 'User' : 'AI'}\n${m.content}\n\n`; }); const blob = new Blob([md], { type: 'text/markdown' }); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `chat-${Date.now()}.md`; a.click(); ui.showToast('Exported', 'success'); }
async function regenLast() { if (state.chatHistory.length < 2) { ui.showToast('No message', 'warning'); return; } const lastAssistantIdx = state.chatHistory.length - 1; const lastUserIdx = state.chatHistory.length - 2; if (state.chatHistory[lastUserIdx].role !== 'user') { ui.showToast('No user message', 'warning'); return; } const lastUserText = state.chatHistory[lastUserIdx].content; state.chatHistory.pop(); ui.renderMessages(); await chat.sendMessage(lastUserText); }
function toggleSelectMode() { state.selectMode = !state.selectMode; const btn = document.getElementById('selectBtn'); const container = document.getElementById('messages'); btn.classList.toggle('active', state.selectMode); btn.textContent = state.selectMode ? '✓ Done' : '☑️ Select'; container.classList.toggle('select-mode-on', state.selectMode); if (!state.selectMode) { state.selectedIndices.clear(); document.getElementById('copyFab').hidden = true; } ui.renderMessages(); }
function updateSelectUI() { const fab = document.getElementById('copyFab'); const count = document.getElementById('selectedCount'); count.textContent = state.selectedIndices.size; fab.hidden = state.selectedIndices.size === 0; document.querySelectorAll('.msg').forEach((msg, i) => { if (state.selectedIndices.has(i)) msg.classList.add('selected-msg'); else msg.classList.remove('selected-msg'); }); }
async function copySelected() { if (state.selectedIndices.size === 0) return; const msgs = Array.from(state.selectedIndices).sort().map(i => state.chatHistory[i]); const text = msgs.map(m => `[${m.role.toUpperCase()}]\n${m.content}`).join('\n\n---\n\n'); try { await utils.copyToClipboard(text); ui.showToast(`Copied ${state.selectedIndices.size} msgs`, 'success'); toggleSelectMode(); } catch (e) { ui.showToast('Copy failed', 'error'); } }
function copyAll(format) { if (state.chatHistory.length === 0) { ui.showToast('No messages', 'warning'); return; } let content = ''; let title = ''; if (format === 'plain') { title = '📄 Plain Text'; content = state.chatHistory.map(m => `[${m.role.toUpperCase()}]\n${m.content}`).join('\n\n---\n\n'); } else if (format === 'md') { title = '📝 Markdown'; content = `# ${document.getElementById('chatTitle').textContent}\n\n**Date:** ${new Date().toLocaleString()}\n\n**Model:** ${state.lastReq.model || 'Unknown'}\n\n---\n\n`; state.chatHistory.forEach(m => { content += `### ${m.role === 'user' ? 'User' : 'AI'}\n${m.content}\n\n`; }); } else if (format === 'json') { title = '📋 JSON'; content = JSON.stringify({ title: document.getElementById('chatTitle').textContent, model: state.lastReq.model || 'Unknown', date: new Date().toISOString(), messages: state.chatHistory.map(m => ({ role: m.role, content: m.content })) }, null, 2); } else if (format === 'html') { title = '🌐 Rich Text'; let html = '<div style="font-family:Inter,sans-serif; max-width:800px; margin:20px auto; padding:20px;">'; html += `<h1 style="color:var(--primary); border-bottom:2px solid var(--primary); padding-bottom:10px;">${utils.escapeHtml(document.getElementById('chatTitle').textContent)}</h1>`; html += `<p style="color:#666;">Date: ${new Date().toLocaleString()}</p>`; state.chatHistory.forEach(m => { const bg = m.role === 'user' ? '#f0e6ff' : '#e6f7ff'; const border = m.role === 'user' ? '#a855f7' : '#00d4ff'; const safeContent = utils.escapeHtml(m.content).replace(/\n/g, '<br>'); html += `<div style="margin:20px 0; padding:15px; border-radius:8px; background:${bg}; border-left:4px solid ${border};"><div style="font-weight:bold; margin-bottom:8px;">${m.role === 'user' ? '👤 You' : '🤖 AI'}</div><div>${safeContent}</div></div>`; }); html += '</div>'; utils.copyToClipboard(html.replace(/<[^>]*>/g, ''), html).then(() => ui.showToast('Rich Text copied', 'success')).catch(() => ui.showToast('Copy failed', 'error')); return; } document.getElementById('modalTitle').textContent = title; document.getElementById('modalContent').value = content; document.getElementById('copyModal').hidden = false; }

async function handleFile(file) { if (!file) return; ui.showToast('Uploading...', 'info'); try { const data = await api.uploadFile(file); if (data.error) { ui.showToast('Error: ' + data.error, 'error'); return; } state.uploadedFileData = data; document.getElementById('fileInfoBox').hidden = false; document.getElementById('fileInfoText').textContent = `📄 ${data.filename} (${data.text_length} chars)`; ui.showToast('Uploaded', 'success'); } catch (e) { ui.showToast('Upload failed', 'error'); } }
function handleSearch(query) { const resBox = document.getElementById('searchResults'); const clearBtn = document.getElementById('searchClearBtn'); if (!query) { resBox.innerHTML = ''; clearBtn.style.display = 'none'; return; } clearBtn.style.display = 'block'; const q = query.toLowerCase(); const results = []; state.chatHistory.forEach((m, i) => { if (m.content && m.content.toLowerCase().includes(q)) { const idx = m.content.toLowerCase().indexOf(q); const start = Math.max(0, idx - 20); const end = Math.min(m.content.length, idx + q.length + 30); results.push({ idx: i, role: m.role, context: m.content.substring(start, end) }); } }); if (results.length === 0) { resBox.innerHTML = '<div style="color:var(--text-muted); font-size:0.75rem; padding:8px;">No results</div>'; return; } resBox.innerHTML = results.map(r => `<div class="search-result-item" data-search-idx="${r.idx}"><div style="font-size:0.75rem; font-weight:600;">${r.role === 'user' ? '👤' : '🤖'}:</div><div style="font-size:0.75rem; color:var(--text-secondary);">...${utils.escapeHtml(r.context)}...</div></div>`).join(''); resBox.querySelectorAll('.search-result-item').forEach(item => { item.addEventListener('click', () => { const idx = parseInt(item.dataset.searchIdx); const msgs = document.querySelectorAll('.msg'); if (msgs[idx]) { msgs[idx].scrollIntoView({ behavior: 'smooth', block: 'center' }); msgs[idx].style.background = 'var(--gradient-soft)'; setTimeout(() => msgs[idx].style.background = '', 2000); } }); }); }
function focusSearch() { document.getElementById('searchInput').focus(); }
function openCommandPalette() { document.getElementById('commandPalette').hidden = false; document.getElementById('commandInput').value = ''; document.getElementById('commandInput').focus(); state.currentCommandIndex = 0; renderCommands(); }
function closeCommandPalette() { document.getElementById('commandPalette').hidden = true; }
function renderCommands(cmds = state.COMMANDS) { const list = document.getElementById('commandList'); if (cmds.length === 0) { list.innerHTML = '<div style="padding:20px; text-align:center; color:var(--text-muted);">No commands</div>'; return; } list.innerHTML = cmds.map((c, i) => `<button class="command-item ${i === state.currentCommandIndex ? 'active' : ''}" data-cmd-idx="${state.COMMANDS.indexOf(c)}"><span>${c.icon} ${c.name}</span>${c.shortcut ? `<span class="command-shortcut">${c.shortcut}</span>` : ''}</button>`).join(''); list.querySelectorAll('.command-item').forEach(item => { item.addEventListener('click', () => { const idx = parseInt(item.dataset.cmdIdx); executeCommand(idx); }); }); }
function executeCommand(index) { const cmd = state.COMMANDS[index]; if (!cmd) return; closeCommandPalette(); const actionMap = { newChat, focusSearch, exportChat, clearChat, toggleSelectMode, themePurple: () => applyTheme('purple'), themeBlue: () => applyTheme('blue'), themeGreen: () => applyTheme('green'), themeOrange: () => applyTheme('orange'), scrollBottom: () => { document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight; }, scrollTop: () => { document.getElementById('messages').scrollTop = 0; } }; if (actionMap[cmd.action]) actionMap[cmd.action](); }
function closeOverlays() { closeCommandPalette(); document.getElementById('contextMenu').hidden = true; if (state.selectMode) toggleSelectMode(); }

const keyboard = {
  init(handlers) {
    this.handlers = handlers;
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); handlers.openCommandPalette(); }
      else if ((e.ctrlKey || e.metaKey) && e.key === 'n') { e.preventDefault(); handlers.newChat(); }
      else if ((e.ctrlKey || e.metaKey) && e.key === 'f') { e.preventDefault(); handlers.focusSearch(); }
      else if ((e.ctrlKey || e.metaKey) && e.key === 'e') { e.preventDefault(); handlers.exportChat(); }
      else if ((e.ctrlKey || e.metaKey) && e.key === 'l') { e.preventDefault(); handlers.clearChat(); }
      else if (e.key === 'Escape') { handlers.closeOverlays(); }
    });
    document.addEventListener('keydown', (e) => {
      const palette = document.getElementById('commandPalette');
      if (palette && !palette.hidden) {
        if (e.key === 'ArrowDown') { e.preventDefault(); state.currentCommandIndex = (state.currentCommandIndex + 1) % state.COMMANDS.length; handlers.renderCommands(); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); state.currentCommandIndex = (state.currentCommandIndex - 1 + state.COMMANDS.length) % state.COMMANDS.length; handlers.renderCommands(); }
        else if (e.key === 'Enter') { e.preventDefault(); handlers.executeCommand(state.currentCommandIndex); }
      }
    });
  }
};