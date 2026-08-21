"""
Context Manager
جلوگیری از memory leak در chat های طولانی
"""
from typing import List, Dict
from config import CONTEXT_LIMITS
from utils.logger import log_debug

class ContextManager:
    """
    Manage chat history with token/message limits
    """
    
    @staticmethod
    def truncate_messages(messages: List[Dict], max_messages: int = None) -> List[Dict]:
        """
        Truncate message history to fit context window
        حفظ آخرین پیام‌ها
        """
        if max_messages is None:
            max_messages = CONTEXT_LIMITS['max_messages']
        
        if len(messages) <= max_messages:
            return messages
        
        # Keep last N messages
        truncated = messages[-max_messages:]
        
        log_debug(f"Truncated {len(messages)} messages to {len(truncated)}")
        
        return truncated
    
    @staticmethod
    def truncate_text(text: str, max_length: int = None) -> str:
        """
        Truncate text to fit context window
        """
        if max_length is None:
            max_length = CONTEXT_LIMITS['max_text_length']
        
        if len(text) <= max_length:
            return text
        
        # Truncate with ellipsis
        truncated = text[:max_length - 3] + "..."
        
        log_debug(f"Truncated text from {len(text)} to {len(truncated)} chars")
        
        return truncated
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Rough token estimation
        ~4 chars per token for English
        ~2 chars per token for Persian/Arabic
        """
        # Detect language
        persian_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        total_chars = len(text)
        
        if total_chars == 0:
            return 0
        
        persian_ratio = persian_chars / total_chars
        
        # Estimate
        if persian_ratio > 0.3:
            # Persian/Arabic
            tokens = total_chars // 2
        else:
            # English
            tokens = total_chars // 4
        
        return tokens
    
    @staticmethod
    def prepare_context(messages: List[Dict]) -> List[Dict]:
        """
        Prepare messages for API call
        Truncate + format
        """
        # Truncate messages
        truncated = ContextManager.truncate_messages(messages)
        
        # Truncate each message content
        prepared = []
        for msg in truncated:
            prepared.append({
                'role': msg['role'],
                'content': ContextManager.truncate_text(msg['content'])
            })
        
        return prepared