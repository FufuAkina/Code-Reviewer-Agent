"""上下文管理器 - 防止对话历史超过 token 限制"""
from typing import List, Dict, Any
import tiktoken

class ContextManager:
    """上下文管理器 - 压缩对话历史"""
    
    # 模型对应的编码器
    MODEL_ENCODINGS = {
        "deepseek-chat": "cl100k_base",   # DeepSeek 使用 GPT-4 同款编码
        "gpt-4": "cl100k_base",
        "gpt-3.5-turbo": "cl100k_base",
        "claude": "cl100k_base",    # 兼容claude
    }
    
    def __init__(self, max_tokens: int = 30000, keep_recent: int = 10,
                 model: str = "deepseek-chat", use_tiktoken: bool = True):
        """
        Args:
            max_tokens: 最大token数(预留2K buffer)
            keep_recent: 始终保留最近 N 条消息
            model: 模型名称(用于选择编码器)
            user_tiktoken: 是否使用tiktoken(False则返回粗略估计)
        """
        self.max_tokens = max_tokens
        self.keep_recent = keep_recent
        self.use_tiktoken = use_tiktoken
        
        # 初始化 tiktoken编码器
        if use_tiktoken:
            try:
                encoding_name = self.MODEL_ENCODINGS.get(model, "cl100k_base")
                self.encoder = tiktoken.get_encoding(encoding_name)
                print(f"✅ 使用 tiktoken 编码器: {encoding_name}")
            except Exception as e:
                print(f"⚠️  tiktoken 初始化失败: {e}，回退到粗略估算")
                self.use_tiktoken = None
                self.encoder = None
        else:
            self.encoder = None
            print("ℹ️  使用粗略估算（未启用 tiktoken）")
            
    def estimate_tokens(self, text: str) -> int:
        """估计 token  数
        
        优先使用 tiktoken(准确), 回退到粗略估计
        """
        if self.use_tiktoken and self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception:
                # tiktoken失败, 回退
                pass
        
        # 粗略估计: 中文1.5字符/token, 英文4字符/token
        return len(text) // 2
    
    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """统计消息列表的总token数"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += self.estimate_tokens(content)
            # 每条消息的metada开销(role, name等)约为4tokens
            total += 4
        return total
        
    def compress(self, messages:  str = List[Dict[str, str]]) -> List[Dict[str, str]]:
        """压缩历史消息
        
        策略:
        1.始终保留第一条(System Prompt)
        2.始终保留最近keep_recent条
        3.如果超过max_tokens, 删除中间的旧消息
        """
        if not messages:
            return messages
        
        # 计算当前 tokens
        current_tokens = self.count_messages_tokens(messages)
        
        # 未超限, 直接返回
        if current_tokens <= self.max_tokens:
            return messages
        
        # 超限, 开始压缩
        print(f"⚠️  上下文超限: {current_tokens} > {self.max_tokens} tokens，开始压缩...")
        
        # 保留第一条+最近的消息
        system_msg = messages[0] if messages[0].get("role") == "system" else None
        recent_messages = messages[-self.keep_recent:]
        
        # 计算保留部分的tokens
        kept_messages = [system_msg] + recent_messages if system_msg else recent_messages
        kept_tokens = self.count_messages_tokens(kept_messages)
        
        # 如果保留部分仍超限, 只能截断最近的消息
        if kept_tokens > self.max_tokens:
            print(f"⚠️  保留部分仍超限，截断为最近 {self.keep_recent // 2} 条")
            kept_messages = [system_msg] + messages[-(self.keep_recent // 2):] if system_msg else messages[-(self.keep_recent // 2):]
            kept_tokens = self.count_messages_tokens(kept_messages)
            
        removed_count = len(messages) - len(kept_messages)
        print(f"✅ 压缩完成: 删除 {removed_count} 条消息, {current_tokens} → {kept_tokens} tokens")
        
        return kept_messages