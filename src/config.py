"""
QuantSeed 配置中心
===============
所有可变参数集中管理，支持环境变量覆盖（Docker 部署）。
"""

import os
import logging

# 加载 .env 文件（本地开发使用）
try:
    from dotenv import load_dotenv
    _env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(_env_file):
        load_dotenv(_env_file)
except ImportError:
    pass  # Docker 环境可能没有 python-dotenv

# ==================== 项目根目录 ====================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ==================== 数据模块配置 ====================
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "daily")  # 本地日线数据存储目录
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")        # 策略信号等输出目录
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")             # 日志文件目录
STOCK_LIST_FILE = os.path.join(DATA_DIR, "..", "hs300_stocks.csv")  # 股票池文件

# 数据下载起始日期
DATA_START_DATE = "20180101"

# 股票池：沪深300成分股代码列表（默认列表，用户可替换hs300_stocks.csv）
# 格式：akshare标准格式，带交易所后缀 .XSHG(上海) / .XSHE(深圳)
DEFAULT_STOCK_POOL = [
    "000001.XSHE",  # 平安银行
    "000002.XSHE",  # 万科A
    "000063.XSHE",  # 中兴通讯
    "000333.XSHE",  # 美的集团
    "000651.XSHE",  # 格力电器
    "000725.XSHE",  # 京东方A
    "000858.XSHE",  # 五粮液
    "002415.XSHE",  # 海康威视
    "002594.XSHE",  # 比亚迪
    "300750.XSHE",  # 宁德时代
    "600000.XSHG",  # 浦发银行
    "600009.XSHG",  # 上海机场
    "600016.XSHG",  # 民生银行
    "600028.XSHG",  # 中国石化
    "600030.XSHG",  # 中信证券
    "600036.XSHG",  # 招商银行
    "600048.XSHG",  # 保利发展
    "600050.XSHG",  # 中国联通
    "600104.XSHG",  # 上汽集团
    "600276.XSHG",  # 恒瑞医药
    "600309.XSHG",  # 万华化学
    "600519.XSHG",  # 贵州茅台
    "600585.XSHG",  # 海螺水泥
    "600809.XSHG",  # 山西汾酒
    "600887.XSHG",  # 伊利股份
    "600900.XSHG",  # 长江电力
    "601012.XSHG",  # 隆基绿能
    "601088.XSHG",  # 中国神华
    "601166.XSHG",  # 兴业银行
    "601318.XSHG",  # 中国平安
    "601398.XSHG",  # 工商银行
    "601668.XSHG",  # 中国建筑
    "601857.XSHG",  # 中国石油
    "601888.XSHG",  # 中国中免
    "603259.XSHG",  # 药明康德
]

# ==================== 策略配置（支持环境变量覆盖） ====================
MA_FAST = int(os.environ.get("MA_FAST", "20"))
MA_SLOW = int(os.environ.get("MA_SLOW", "60"))
POSITION_SIZE = float(os.environ.get("POSITION_SIZE", "0.95"))

# ==================== 回测引擎配置 ====================
INITIAL_CASH = float(os.environ.get("INITIAL_CASH", "1000000.0"))
COMMISSION_RATE = float(os.environ.get("COMMISSION_RATE", "0.00025"))
SLIPPAGE = float(os.environ.get("SLIPPAGE", "0.001"))

# ==================== 后端 API 地址 ====================
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# ==================== 日志配置 ====================
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ==================== Web界面配置 ====================
PAGE_TITLE = "QuantSeed 量化种子 - 回测与策略监控平台"
PAGE_LAYOUT = "wide"
SIDEBAR_STATE = "expanded"


def ensure_dirs():
    """确保所有必要目录存在"""
    for d in [DATA_DIR, OUTPUT_DIR, LOG_DIR]:
        os.makedirs(d, exist_ok=True)


def setup_logging(name: str = "QuantSeed") -> logging.Logger:
    """
    配置并返回日志记录器。

    第二阶段扩展点：可改为同时输出到文件、远程日志服务（如ELK）、
    或通过消息队列推送关键交易日志。
    """
    ensure_dirs()
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 文件输出（第二阶段自动交易会重度依赖此日志文件）
    log_file = os.path.join(LOG_DIR, "quantseed.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(LOG_LEVEL)
    file_formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger
