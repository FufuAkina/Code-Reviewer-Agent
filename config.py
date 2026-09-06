# config.py - 配置管理模块
"""
配置管理：加载环境变量，验证API配置    
"""

import os 
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

class Config:
    """配置类：集中管理所有配置项"""
    
    # API配置
    API_KEY = os.getenv("DEEPSEEK_API_KEY")
    BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    MODEL = "deepseek-chat"  # DEEPSEEK模型名
    
    # 请求参数
    MAX_TOKENS = 2000
    TEMPERATURE = 0.3
    
    # 提示词模板配置
    DEFAULT_TEMPLATE = "detailed"   # 默认使用详细分析模板
    PROMPTS_DIR = "prompts"         # 提示词目录
    
    # 重试机制配置
    RETRY_MAX_ATTEMPTS = 3   # 最大重试次数  
    RETRY_BASE_DELAY = 1.0   # 基础延迟(秒)
    RETRY_MAX_DELAY = 60.0   # 最大延迟(秒)
    
    # 速率限制配置（任务 5.2 新增）
    RATE_LIMIT_ENABLED = True       # 是否启用速率限制
    RATE_LIMIT_RATE = 0.13          # 每秒最多请求数（免费用户：10 RPM = 0.167 RPS，保守取 0.13）
    RATE_LIMIT_CAPACITY = 2.0       # token桶容量（允许初始突发 2 个请求）
    
    @classmethod
    def validate(cls) -> bool:
        """
        验证配置是否完整
        
        Return:
            True:配置正确
            
        Raise:
            ValueError:缺少必要配置
        """
        if not cls.API_KEY:
            raise ValueError(
                 "❌ 缺少 API Key！\n"
                "请在 .env 文件中设置:\n"
                "DEEPSEEK_API_KEY=your_api_key"   
            )
            
        if not cls.API_KEY.startswith("sk-"):
            raise ValueError(
                "❌ API Key 格式错误！\n"
                "应该以 'sk-' 开头"
            )
            
        print("✅ 配置验证通过")
        return True
    
    @classmethod
    def show(cls):
        """显示当前配置(隐藏敏感信息)"""
        print("\n" + "=" * 60)
        print("当前配置:")
        print("=" * 60)
        print(f"Base URL: {cls.BASE_URL}")
        print(f"API Key: {cls.API_KEY[:10]}...{cls.API_KEY[-4:]}")
        print(f"Model: {cls.MODEL}")
        print(f"Max Tokens: {cls.MAX_TOKENS}")
        print(f"Temperature: {cls.TEMPERATURE}")
        print(f"Rate Limit: {cls.RATE_LIMIT_ENABLED} ({cls.RATE_LIMIT_RATE} req/s)")
        print("=" * 60 + "\n")
        
# 模块导入时自动验证
if __name__ == "__main__":
    # 测试配置
    try:
        Config.validate()
        Config.show()
    except ValueError as e:
        print(e)
