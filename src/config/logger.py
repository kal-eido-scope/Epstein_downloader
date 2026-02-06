import logging
from datetime import datetime
from pathlib import Path

def init_logger(name: str,log_file: str|Path,level=logging.INFO) -> logging.Logger:
    """初始化日志记录器"""
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, 'a') as f:
        f.write(f"================================{{{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}}================================\n")
    logger = logging.getLogger(name)
    logger.setLevel(level)

    fh = logging.FileHandler(log_file, mode='a',encoding='utf-8')
    fh.setLevel(level)

    ch = logging.StreamHandler()
    ch.setLevel(level)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger