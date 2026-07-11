"""
QuantSeed 数据库模块 - database.py
==================================
支持 SQLite（本地开发）和 PostgreSQL（生产环境）。

数据库设计：
1. stock_info        - 股票基本信息
2. daily_data        - 日线行情数据
3. signal_records    - 交易信号记录
4. backtest_results  - 回测结果
5. system_config     - 系统配置
6. user_watchlist    - 用户自选股（第二阶段）
7. trade_logs        - 交易日志（第二阶段）
"""

import os
import sys
import json
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DATA_DIR, PROJECT_ROOT, ensure_dirs

# ==================== 数据库引擎选择 ====================
# 通过环境变量 DB_TYPE 切换：sqlite（默认）或 postgresql
DB_TYPE = os.environ.get("DB_TYPE", "sqlite").lower()

# 确保数据库文件所在目录存在，使用 PROJECT_ROOT 绝对路径避免工作目录不同导致的问题
_db_dir = os.path.join(PROJECT_ROOT, "data")
os.makedirs(_db_dir, exist_ok=True)

# DB_PATH 默认值基于项目根目录
_env_db_path = os.environ.get("DB_PATH", "")
if _env_db_path:
    # 如果环境变量设置了相对路径，基于 PROJECT_ROOT 解析
    if not os.path.isabs(_env_db_path):
        DB_PATH = os.path.join(PROJECT_ROOT, _env_db_path)
    else:
        DB_PATH = _env_db_path
else:
    DB_PATH = os.path.join(_db_dir, "quantseed.db")

# PostgreSQL 连接参数（从环境变量读取）
PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_PORT = os.environ.get("PG_PORT", "5432")
PG_USER = os.environ.get("PG_USER", "quantseed")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "")
PG_DATABASE = os.environ.get("PG_DATABASE", "quantseed")

# ==================== SQLAlchemy 初始化 ====================
from sqlalchemy import (
    create_engine, Column, Integer, BigInteger, String, Float,
    Date, DateTime, Boolean, Text, JSON, Index, text,
)
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

Base = declarative_base()

_engine = None
_SessionLocal = None


def _get_engine():
    """懒加载数据库引擎（避免模块导入时立即连接）"""
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine

    ensure_dirs()
    os.makedirs(_db_dir, exist_ok=True)

    if DB_TYPE == "postgresql":
        DATABASE_URL = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"
        _engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
    else:
        # SQLite: 使用绝对路径 + creator 避免 URI 编码问题（Windows 中文用户名）
        import sqlite3
        db_path = os.path.abspath(DB_PATH)
        _engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            creator=lambda: sqlite3.connect(db_path, check_same_thread=False),
        )

    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def _get_session_local():
    """获取 SessionLocal"""
    global _SessionLocal
    if _SessionLocal is None:
        _get_engine()
    return _SessionLocal


# 为了向后兼容，保留 engine 属性（懒加载）
@property
def _engine_prop():
    return _get_engine()


def get_db():
    """获取数据库会话（依赖注入用）"""
    db = _get_session_local()()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """直接获取数据库会话（非 FastAPI 场景使用）"""
    return _get_session_local()()


# ==================== 数据模型定义 ====================

class StockInfo(Base):
    """股票基本信息表"""
    __tablename__ = "stock_info"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False, index=True, comment="股票代码")
    name = Column(String(50), comment="股票名称")
    exchange = Column(String(10), comment="交易所: XSHG/XSHE")
    market = Column(String(10), comment="市场: 沪深主板/创业板/科创板")
    industry = Column(String(50), comment="行业分类")
    is_active = Column(Boolean, default=True, comment="是否在股票池中")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<StockInfo {self.code} {self.name}>"


class DailyData(Base):
    """日线行情数据表"""
    __tablename__ = "daily_data"
    __table_args__ = (
        Index("idx_daily_code_date", "code", "trade_date", unique=True),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(20), nullable=False, index=True, comment="股票代码")
    trade_date = Column(Date, nullable=False, comment="交易日期")
    open = Column(Float, comment="开盘价")
    high = Column(Float, comment="最高价")
    low = Column(Float, comment="最低价")
    close = Column(Float, comment="收盘价")
    volume = Column(BigInteger, comment="成交量(股)")
    amount = Column(Float, comment="成交额(元)")
    amplitude = Column(Float, comment="振幅(%)")
    pct_change = Column(Float, comment="涨跌幅(%)")
    change_amount = Column(Float, comment="涨跌额")
    turnover = Column(Float, comment="换手率(%)")
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<DailyData {self.code} {self.trade_date}>"


class SignalRecord(Base):
    """交易信号记录表"""
    __tablename__ = "signal_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(20), nullable=False, index=True, comment="股票代码")
    signal_date = Column(Date, nullable=False, comment="信号日期")
    signal_type = Column(String(20), nullable=False, comment="信号类型: golden_cross/death_cross")
    close_price = Column(Float, comment="信号时收盘价")
    ma_fast = Column(Float, comment=f"快线值")
    ma_slow = Column(Float, comment=f"慢线值")
    divergence = Column(Float, comment="乖离率(%)")
    trend = Column(String(20), comment="当前趋势: bull/bear/neutral")
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_signal_code_date_type", "code", "signal_date", "signal_type", unique=True),
    )

    def __repr__(self):
        return f"<SignalRecord {self.code} {self.signal_date} {self.signal_type}>"


class BacktestResult(Base):
    """回测结果表"""
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), nullable=False, index=True, comment="股票代码")
    start_date = Column(Date, nullable=False, comment="回测起始日期")
    end_date = Column(Date, nullable=False, comment="回测结束日期")
    strategy = Column(String(50), comment="策略名称")
    initial_cash = Column(Float, comment="初始资金")
    final_value = Column(Float, comment="最终权益")
    total_return = Column(Float, comment="总收益率(%)")
    annual_return = Column(Float, comment="年化收益率(%)")
    sharpe_ratio = Column(Float, comment="夏普比率")
    max_drawdown = Column(Float, comment="最大回撤(%)")
    win_rate = Column(Float, comment="胜率(%)")
    profit_loss_ratio = Column(Float, comment="盈亏比")
    total_trades = Column(Integer, comment="总交易次数")
    details = Column(JSON, comment="详细回测结果(JSON)")
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<BacktestResult {self.code} {self.start_date}-{self.end_date}>"


class SystemConfig(Base):
    """系统配置表（第二阶段扩展：参数热更新）"""
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(50), unique=True, nullable=False, comment="配置键")
    config_value = Column(Text, comment="配置值")
    config_type = Column(String(20), default="string", comment="值类型: string/int/float/bool/json")
    description = Column(Text, comment="配置说明")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<SystemConfig {self.config_key}={self.config_value}>"


# ==================== 数据库初始化 ====================

def init_db():
    """创建所有表并初始化默认配置"""
    eng = _get_engine()
    Base.metadata.create_all(bind=eng)

    # 初始化系统默认配置
    db = get_db_session()
    try:
        _init_default_config(db)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _init_default_config(db):
    """插入默认系统配置（如果不存在）"""
    defaults = [
        ("ma_fast", "20", "int", "快线周期"),
        ("ma_slow", "60", "int", "慢线周期"),
        ("initial_cash", "1000000", "float", "初始资金"),
        ("position_size", "0.95", "float", "仓位比例"),
        ("commission_rate", "0.00025", "float", "手续费率"),
        ("slippage", "0.001", "float", "滑点"),
        ("data_start_date", "20180101", "string", "数据起始日期"),
    ]
    for key, value, vtype, desc in defaults:
        existing = db.query(SystemConfig).filter_by(config_key=key).first()
        if not existing:
            db.add(SystemConfig(config_key=key, config_value=value, config_type=vtype, description=desc))


# ==================== 数据迁移工具 ====================

def migrate_csv_to_db():
    """将本地 CSV 数据迁移到数据库（一次性操作）"""
    import pandas as pd

    db = get_db_session()
    try:
        daily_dir = DATA_DIR
        if not os.path.exists(daily_dir):
            print(f"数据目录不存在: {daily_dir}")
            return

        files = [f for f in os.listdir(daily_dir) if f.endswith(".csv")]
        total = 0

        for filename in files:
            code = filename.replace(".csv", "")
            filepath = os.path.join(daily_dir, filename)

            # 检查是否已导入
            existing_count = db.query(DailyData).filter_by(code=code).count()
            if existing_count > 0:
                print(f"  {code}: 已存在 {existing_count} 条记录，跳过")
                continue

            df = pd.read_csv(filepath, dtype={"日期": str})
            if df.empty:
                continue

            rows = []
            for _, row in df.iterrows():
                try:
                    rows.append(DailyData(
                        code=code,
                        trade_date=datetime.strptime(row["日期"], "%Y-%m-%d").date(),
                        open=float(row.get("开盘", 0)) if pd.notna(row.get("开盘", 0)) else None,
                        high=float(row.get("最高", 0)) if pd.notna(row.get("最高", 0)) else None,
                        low=float(row.get("最低", 0)) if pd.notna(row.get("最低", 0)) else None,
                        close=float(row.get("收盘", 0)) if pd.notna(row.get("收盘", 0)) else None,
                        volume=int(row.get("成交量", 0)) if pd.notna(row.get("成交量", 0)) else 0,
                        amount=float(row.get("成交额", 0)) if pd.notna(row.get("成交额", 0)) else None,
                        amplitude=float(row.get("振幅", 0)) if pd.notna(row.get("振幅", 0)) else None,
                        pct_change=float(row.get("涨跌幅", 0)) if pd.notna(row.get("涨跌幅", 0)) else None,
                        change_amount=float(row.get("涨跌额", 0)) if pd.notna(row.get("涨跌额", 0)) else None,
                        turnover=float(row.get("换手率", 0)) if pd.notna(row.get("换手率", 0)) else None,
                    ))
                except Exception:
                    continue

            if rows:
                db.bulk_save_objects(rows)
                db.commit()
                total += len(rows)
                print(f"  {code}: 导入 {len(rows)} 条记录")

        print(f"\n总计导入 {total} 条数据记录")

    except Exception as e:
        db.rollback()
        print(f"数据迁移失败: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    # 直接运行此脚本可执行数据库初始化和数据迁移
    print("初始化数据库...")
    init_db()
    print(f"数据库已就绪: {DATABASE_URL}")
    print(f"数据库类型: {DB_TYPE}")

    # 迁移现有CSV数据
    if DB_TYPE == "sqlite":
        print("\n是否迁移本地CSV数据到数据库？运行: migrate_csv_to_db()")
