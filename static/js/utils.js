// Utility Functions Module
export const utils = {
  escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },
  
  checkRTL(el) {
    if (!el || !el.value) return;
    const text = el.value;
    const rtl = (text.match(/[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/g) || []).length;
    const latin = (text.match(/[a-zA-Z]/g) || []).length;
    el.classList.toggle('rtl', rtl > latin);
  },
  
  isRTL(text) {
    if (!text) return false;
    return /[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF]/.test(text);
  },
  
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
        if (html) {
          await navigator.clipboard.write([
            new ClipboardItem({
              'text/html': new Blob([html], { type: 'text/html' }),
              'text/plain': new Blob([text], { type: 'text/plain' })
            })
          ]);
          return;
        } else {
          await navigator.clipboard.writeText(text);
          return;
        }
      } catch (e) {
        console.warn('Clipboard API failed:', e);
      }
    }
    
    return new Promise((resolve, reject) => {
      try {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.cssText = 'position:fixed;top:0;left:0;width:2em;height:2em;padding:0;border:none;outline:none;box-shadow:none;background:transparent;opacity:0';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        
        let success = false;
        try {
          success = document.execCommand('copy');
        } catch (e) {
          success = false;
        }
        
        document.body.removeChild(textarea);
        
        if (success) resolve();
        else reject(new Error('execCommand failed'));
      } catch (e) {
        reject(e);
      }
    });
  },
  
  generateId() {
    return 'id_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  },
  
  truncate(str, length = 30) {
    if (!str) return '';
    return str.length > length ? str.substring(0, length) : str;
  },
  
  encryptKey(key) {
    const xorKey = 'aistudio2026';
    let result = '';
    for (let i = 0; i < key.length; i++) {
      result += String.fromCharCode(key.charCodeAt(i) ^ xorKey.charCodeAt(i % xorKey.length));
    }
    return btoa(result);
  },
  
  decryptKey(encrypted) {
    try {
      const xorKey = 'aistudio2026';
      const decoded = atob(encrypted);
      let result = '';
      for (let i = 0; i < decoded.length; i++) {
        result += String.fromCharCode(decoded.charCodeAt(i) ^ xorKey.charCodeAt(i % xorKey.length));
      }
      return result;
    } catch (e) {
      return encrypted;
    }
  },
  
  maskKey(key) {
    if (!key || key.length < 10) return key || '';
    return key.substring(0, 6) + '••••' + key.substring(key.length - 4);
  },
  
  safeHostname(url) {
    try {
      return new URL(url).hostname;
    } catch (e) {
      return '';
    }
  }
};