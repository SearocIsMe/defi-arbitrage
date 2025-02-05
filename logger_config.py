import logging
import logging.handlers
import os
from datetime import datetime

# 创建logs目录
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 生成日志文件名(按日期)
current_date = datetime.now().strftime("%Y-%m-%d")
LOG_FILE = os.path.join(LOG_DIR, f"arbitrage_{current_date}.log")

# 创建logger
logger = logging.getLogger("ArbitrageBot")
logger.setLevel(logging.DEBUG)

# 日志格式
log_format = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(log_format)

# 文件处理器(按天滚动)
file_handler = logging.handlers.TimedRotatingFileHandler(
    LOG_FILE,
    when="midnight",
    interval=1,
    backupCount=30,  # 保留30天的日志
    encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(log_format)

# 添加处理器
logger.addHandler(console_handler)
logger.addHandler(file_handler)

def get_logger(name=None):
    """
    获取logger实例
    :param name: logger名称
    :return: logger实例
    """
    if name:
        return logging.getLogger(f"ArbitrageBot.{name}")
    return logger
