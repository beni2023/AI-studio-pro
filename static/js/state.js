// State Management Module
export const state = {
  chatHistory: [],
  currentChatId: null,
  allChats: [],
  lastReq: {},
  isStreaming: false,
  abortCtrl: null,
  selectMode: false,
  selectedIndices: new Set(),
  currentImage: null,
  uploadedFileData: null,
  currentCommandIndex: 0,
  searchDebounceTimer: null,
  activeToasts: [],
  MAX_TOASTS: 4,
  modelsLoaded: false,
  assistantIndex: -1,
  
  COMMANDS: [
    { name: 'New Chat', icon: '✨', shortcut: 'Ctrl+N', action: 'newChat' },
    { name: 'Search', icon: '🔍', shortcut: 'Ctrl+F', action: 'focusSearch' },
    { name: 'Export', icon: '📤', shortcut: 'Ctrl+E', action: 'exportChat' },
    { name: 'Clear Chat', icon: '🗑️', shortcut: 'Ctrl+L', action: 'clearChat' },
    { name: 'Optimize', icon: '✨', shortcut: '', action: 'optimizePrompt' },
    { name: 'Select Mode', icon: '☑️', shortcut: '', action: 'toggleSelectMode' },
    { name: 'Theme Purple', icon: '🟣', shortcut: '', action: 'themePurple' },
    { name: 'Theme Blue', icon: '🔵', shortcut: '', action: 'themeBlue' },
    { name: 'Theme Green', icon: '🟢', shortcut: '', action: 'themeGreen' },
    { name: 'Theme Orange', icon: '🟠', shortcut: '', action: 'themeOrange' },
    { name: 'Scroll Bottom', icon: '⬇️', shortcut: 'End', action: 'scrollBottom' },
    { name: 'Scroll Top', icon: '⬆️', shortcut: 'Home', action: 'scrollTop' },
  ]
};

// Custom Providers System
export const customProviders = {
  STORAGE_KEY: 'custom_providers',
  
  getAll() {
    try {
      return JSON.parse(localStorage.getItem(this.STORAGE_KEY)) || [];
    } catch (e) {
      return [];
    }
  },
  
  save(providers) {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(providers));
    } catch (e) {
      console.error('Error saving custom providers:', e);
    }
  },
  
  add(provider) {
    const providers = this.getAll();
    const newProvider = {
      id: 'cp_' + Date.now(),
      ...provider,
      createdAt: Date.now()
    };
    providers.push(newProvider);
    this.save(providers);
    return newProvider;
  },
  
  remove(id) {
    const providers = this.getAll().filter(p => p.id !== id);
    this.save(providers);
  },
  
  getByUrl(url) {
    return this.getAll().find(p => p.url === url);
  }
};