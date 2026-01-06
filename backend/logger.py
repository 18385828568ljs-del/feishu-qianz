"""
日志配置模块
提供统一的日志格式和轮转策略
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime


# 日志目录
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# 日志格式
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 日志级别（可通过环境变量配置）
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()


def get_logger(name: str = None) -> logging.Logger:
    """
    获取配置好的 logger
    
    Args:
        name: logger 名称，默认为 'app'
    
    Returns:
        配置好的 Logger 实例
    """
    logger_name = name or 'app'
    logger = logging.getLogger(logger_name)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    
    # 控制台 Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(console_handler)
    
    # 文件 Handler（带轮转）
    log_file = os.path.join(LOG_DIR, f'{logger_name}.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(file_handler)
    
    # 错误日志单独文件
    error_log_file = os.path.join(LOG_DIR, f'{logger_name}_error.log')
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(error_handler)
    
    return logger


# 创建默认 logger
app_logger = get_logger('app')
form_logger = get_logger('form')
quota_logger = get_logger('quota')


def log_api_request(logger: logging.Logger, method: str, path: str, params: dict = None):
    """记录 API 请求"""
    logger.info(f"[API] {method} {path} params={params}")


def log_api_response(logger: logging.Logger, method: str, path: str, status: int, duration_ms: float = None):
    """记录 API 响应"""
    duration_str = f" ({duration_ms:.2f}ms)" if duration_ms else ""
    logger.info(f"[API] {method} {path} -> {status}{duration_str}")


def log_feishu_api(logger: logging.Logger, api_name: str, status: str, details: str = None):
    """记录飞书 API 调用"""
    msg = f"[Feishu] {api_name} -> {status}"
    if details:
        msg += f" | {details}"
    logger.info(msg)


def log_error(logger: logging.Logger, error_type: str, message: str, details: dict = None):
    """记录错误"""
    msg = f"[Error] {error_type}: {message}"
    if details:
        msg += f" | {details}"
    logger.error(msg)
