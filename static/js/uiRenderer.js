// UI Renderer Module - Handles all DOM rendering and UI updates
import { utils } from './utils.js';

export const uiRenderer = {
  renderMessages(container, chatHistory, selectedIndices, assistantIndex) {
    if (!container) return;

    if (chatHistory.length === 0) {
      container.innerHTML = this.getEmptyStateHTML();
      this.updateMsgCount(0);
      return;
    }

    container.innerHTML = chatHistory.map((m, i) => {
      const isUser = m.role === 'user';
      const isChecked = selectedIndices.has(i) ? 'checked' : '';
      
      let imageHtml = '';
      if (m.image) {
        imageHtml = `<div class="msg-image-container">
          <img src="${m.image}" alt="Image" class="msg-image" data-action="open-image">
          <div class="msg-image-actions">
            <button class="msg-image-btn" data-action="download-image" data-idx="${i}">⬇️</button>
            <button class="msg-image-btn" data-action="copy-image" data-idx="${i}">📋</button>
          </div>
        </div>`;
      }

      let contentHtml = '';
      if (m.streaming) {
        contentHtml = '';
      } else {
        const isRtl = utils.isRTL(m.content);
        contentHtml = `<div class="md ${isRtl ? 'rtl' : ''}">${utils.formatMarkdown(m.content || '')}</div>`;
      }

      const checkbox = `<input type="checkbox" class="msg-cb" ${isChecked} data-idx="${i}">`;
      
      let actions = '';
      if (!isUser && m.content && !m.streaming) {
        actions = `<div class="msg-actions">
          <button class="msg-action" data-action="copy-msg" data-idx="${i}">📋 Copy</button>
          <button class="msg-action" data-action="edit-msg" data-idx="${i}" title="Edit message">✏️</button>
          <button class="msg-action" data-action="regen-msg" data-idx="${i}" title="Regenerate response">🔄</button>
        </div>`;
      }

      let longMsgClass = '';
      let toggleBtn = '';
      if (!isUser && m.content && m.content.length > 1200 && !m.streaming) {
        longMsgClass = 'long-msg';
        toggleBtn = `<button class="toggle-long-btn" data-action="toggle-long">Show more ▼</button>`;
      }

      return `<div class="msg ${isUser ? 'user' : ''} ${selectedIndices.has(i) ? 'selected-msg' : ''}" data-idx="${i}">
        ${checkbox}
        <div class="avatar">${isUser ? '👤' : '🤖'}</div>
        <div class="bubble ${longMsgClass}">
          ${imageHtml}
          ${contentHtml}
          ${actions}
          ${toggleBtn}
        </div>
      </div>`;
    }).join('');

    this.addCodeCopyButtons();
    this.updateMsgCount(chatHistory.length);
    container.scrollTop = container.scrollHeight;
  },

  updateStreamingMessage(container, assistantIndex, text) {
    const msgs = container.querySelectorAll('.msg');
    const lastMsg = msgs[assistantIndex];
    if (!lastMsg) return;

    const bubble = lastMsg.querySelector('.bubble');
    if (!bubble) return;

    let streamEl = bubble.querySelector('.streaming-text');
    if (!streamEl) {
      const isRtl = utils.isRTL(text);
      streamEl = document.createElement('div');
      streamEl.className = `streaming-text md ${isRtl ? 'rtl' : ''}`;
      bubble.appendChild(streamEl);
    }

    streamEl.innerHTML = utils.formatMarkdown(text);
    this.addCodeCopyButtons();
    container.scrollTop = container.scrollHeight;
  },

  addCodeCopyButtons() {
    document.querySelectorAll('.code-copy-btn').forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        const pre = btn.closest('pre');
        const code = pre.querySelector('code');
        const text = code.innerText;
        
        utils.copyToClipboard(text).then(() => {
          btn.classList.add('copied');
          btn.innerHTML = '✓ Copied!';
          setTimeout(() => {
            btn.classList.remove('copied');
            btn.innerHTML = '📋 Copy';
          }, 2000);
        }).catch(() => {
          // Show error toast if available
        });
      };
    });
  },

  getEmptyStateHTML() {
    return `<div class="empty">
      <svg class="empty-icon" viewBox="0 0 120 120" fill="none">
        <circle cx="60" cy="60" r="50" stroke="url(#grad1)" stroke-width="2" opacity="0.3"/>
        <path d="M40 50 Q60 30 80 50 Q80 70 60 80 Q40 70 40 50" stroke="url(#grad1)" stroke-width="2" fill="none"/>
        <circle cx="50" cy="55" r="3" fill="var(--primary)"/>
        <circle cx="70" cy="55" r="3" fill="var(--secondary)"/>
        <path d="M50 65 Q60 72 70 65" stroke="url(#grad1)" stroke-width="2" fill="none" stroke-linecap="round"/>
        <defs>
          <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:var(--primary)"/>
            <stop offset="100%" style="stop-color:var(--secondary)"/>
          </linearGradient>
        </defs>
      </svg>
      <h2>Welcome to AI Studio Pro</h2>
      <p>Start a conversation with any AI model</p>
      <div class="chips">
        <div class="chip" data-chip="Write a Python function">💻 Python</div>
        <div class="chip" data-chip="یه داستان کوتاه بنویس">📖 داستان</div>
        <div class="chip" data-chip="Explain quantum computing">🔬 Explain</div>
      </div>
    </div>`;
  },

  updateMsgCount(count) {
    const el = document.getElementById('msgCount');
    if (el) el.textContent = `${count} msgs`;
  },

  updateModelInfo(modelName) {
    const el = document.getElementById('modelInfo');
    if (el) el.textContent = modelName || 'No model';
  },

  updateChatTitle(title) {
    const el = document.getElementById('chatTitle');
    if (el) el.textContent = title || 'Untitled';
  },

  showToast(msg, type = 'info') {
    // Simple toast implementation
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = msg;
    toast.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      padding: 12px 24px;
      border-radius: 8px;
      background: var(--primary, #8b5cf6);
      color: white;
      z-index: 9999;
      animation: slideIn 0.3s ease;
    `;
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.style.animation = 'slideOut 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }
};
