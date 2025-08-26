import logging
import logging.handlers
import os
from wechat_articles.core.config import Config

def get_logger(name):
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(getattr(logging, Config.LOG_CONFIG['level']))
        
        # 创建日志目录
        log_dir = os.path.dirname(Config.LOG_CONFIG['file_path'])
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 文件处理器
        file_handler = logging.handlers.RotatingFileHandler(
            Config.LOG_CONFIG['file_path'],
            maxBytes=Config.LOG_CONFIG['max_size'],
            backupCount=Config.LOG_CONFIG['backup_count'],
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 格式化器
        formatter = logging.Formatter(Config.LOG_CONFIG['format'])
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger

def log_performance(func_name, duration, success=True, error=None):
    logger = get_logger('performance')
    status = 'SUCCESS' if success else 'FAILED'
    
    if error:
        logger.warning(f'PERF [{func_name}] {status} - {duration:.3f}s - Error: {error}')
    else:
        logger.info(f'PERF [{func_name}] {status} - {duration:.3f}s')

def log_collector_activity(collector_name, action, details=None):
    logger = get_logger('collector')
    message = f'[{collector_name}] {action}'
    if details:
        message += f' - {details}'
    logger.info(message)