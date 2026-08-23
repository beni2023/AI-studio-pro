// Chat Service Module - Handles all API and messaging logic
import { utils } from './utils.js';

export const chatService = {
  abortController: null,
  isStreaming: false,

  async sendMessage(messages, providerId, model, onChunk, onComplete, onError) {
    if (this.isStreaming) {
      throw new Error('Already streaming');
    }

    this.isStreaming = true;
    this.abortController = new AbortController();
    
    let fullText = '';
    let hasError = false;

    try {
      const response = await fetch('/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: providerId,
          model,
          messages
        }),
        signal: this.abortController.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;

          const rawData = line.slice(6).trim();
          if (!rawData || rawData === '[DONE]') continue;

          try {
            const data = JSON.parse(rawData);

            if (data.error) {
              hasError = true;
              onError(new Error(data.error));
              break;
            }

            if (data.done === true) continue;

            let extractedText = '';
            if (typeof data === 'string') {
              extractedText = data;
            } else if (data.text) {
              extractedText = data.text;
            } else if (data.choices?.[0]) {
              extractedText = data.choices[0].delta?.content || data.choices[0].text || '';
            } else if (data.choices?.[0]?.message) {
              extractedText = data.choices[0].message.content || '';
            } else if (data.response) {
              extractedText = data.response;
            }

            if (extractedText) {
              fullText += extractedText;
              onChunk(fullText);
            }
          } catch (e) {
            console.error('Parse error:', e, 'Line:', line);
          }
        }

        if (hasError) break;
      }

      if (!hasError) {
        onComplete(fullText);
      }

    } catch (error) {
      if (error.name === 'AbortError') {
        onError(new Error('Stopped by user'));
      } else {
        onError(error);
      }
    } finally {
      this.isStreaming = false;
      this.abortController = null;
    }
  },

  stopStreaming() {
    if (this.abortController && !this.abortController.signal.aborted) {
      this.abortController.abort();
    }
    this.isStreaming = false;
  },

  async uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/upload_file', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  }
};
