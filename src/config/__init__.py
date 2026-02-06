from .consts import BASE_DIR, PAGE_DIR, FILE_DIR, LOG_DIR
from .default_session import default_session as session
from .logger import init_logger

def get_settings():
    """读取配置"""
    from .base import Settings
    return Settings()

__all__ = ['BASE_DIR', 'PAGE_DIR', 'FILE_DIR', 'LOG_DIR'
           ,'session','init_logger','get_settings']