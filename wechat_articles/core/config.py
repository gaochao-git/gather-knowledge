import os
from pathlib import Path

class Config:
    """系统配置类"""
    
    # 基础路径
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / 'data'
    LOGS_DIR = BASE_DIR / 'logs'
    ARTICLES_DIR = BASE_DIR / 'articles'
    
    # 确保目录存在
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    
    # 日志配置
    LOG_CONFIG = {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file_path': str(LOGS_DIR / 'wechat_collector.log'),
        'max_size': 10 * 1024 * 1024,  # 10MB
        'backup_count': 5
    }
    
    # Flask配置
    FLASK_CONFIG = {
        'host': '0.0.0.0',
        'port': 5000,
        'debug': True
    }
    
    # 采集配置
    COLLECTOR_CONFIG = {
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'request_timeout': 30,
        'retry_times': 3,
        'delay_between_requests': 2,
        'max_articles_per_account': 100
    }
    
    # 搜索配置
    SEARCH_CONFIG = {
        'sogou_base_url': 'https://weixin.sogou.com/weixin',
        'search_type_account': 1,
        'search_type_article': 2
    }
    
    @classmethod
    def get_article_dir(cls, account_name):
        """获取账号文章存储目录"""
        safe_name = "".join(c for c in account_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        return cls.ARTICLES_DIR / safe_name
    
    @classmethod
    def get_export_dir(cls, account_name):
        """获取账号导出文件目录"""
        return cls.get_article_dir(account_name) / 'exports'