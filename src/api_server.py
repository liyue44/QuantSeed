"""
QuantSeed 后端 API 服务 - api_server.py
======================================
FastAPI 后端，提供数据、信号、回测等 REST API 接口。
前端（Streamlit）通过 HTTP 调用后端 API 获取数据。

启动方式:
    uvicorn api_server:app --host 0.0.0.0 --port 8000
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Optional, List
from contextlib import asynccontextmanager

import pandas as pd
import numpy as np
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import akshare as ak

# 添加 src 到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    DATA_DIR, OUTPUT_DIR, LOG_DIR, MA_FAST, MA_SLOW,
    INITIAL_CASH, COMMISSION_RATE, SLIPPAGE,
    DEFAULT_STOCK_POOL, DATA_START_DATE,
    ensure_dirs, setup_logging,
)
from data_manager import DataManager
from signal_generator import SignalGenerator
from backtest_engine import BacktestEngine

# ==================== 数据库模块（SQLite 本地存储） ====================
from database import (
    init_db, get_db, get_db_session, StockInfo, DailyData, SignalRecord,
    BacktestResult, SystemConfig, UserStock,
)

logger = setup_logging("APIServer")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库，关闭时清理"""
    ensure_dirs()
    init_db()
    logger.info("数据库初始化完成")
    yield
    logger.info("API 服务关闭")


app = FastAPI(
    title="QuantSeed API",
    description="QuantSeed 量化种子后端服务 - 数据、信号、回测",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置：允许 Streamlit 前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局实例（懒加载）
_data_manager: Optional[DataManager] = None
_signal_generator: Optional[SignalGenerator] = None
_backtest_engine: Optional[BacktestEngine] = None


def get_dm() -> DataManager:
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager()
    return _data_manager


def get_sg() -> SignalGenerator:
    global _signal_generator
    if _signal_generator is None:
        _signal_generator = SignalGenerator()
    return _signal_generator


def get_be() -> BacktestEngine:
    global _backtest_engine
    if _backtest_engine is None:
        _backtest_engine = BacktestEngine()
    return _backtest_engine


# ==================== 健康检查 ====================
@app.get("/api/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ==================== 股票信息 ====================
@app.get("/api/stocks")
def list_stocks():
    """获取股票池列表（默认35只 + 用户自定义）"""
    dm = get_dm()
    available = dm.get_available_stocks()

    # 获取用户自定义股票列表
    db = get_db_session()
    try:
        user_codes = set(row[0] for row in db.query(UserStock.code).all())
    except Exception:
        user_codes = set()
    finally:
        db.close()

    result = []
    for code in dm.stock_pool:
        result.append({
            "code": code,
            "name": dm.get_stock_name(code),
            "has_data": code in available,
            "is_custom": code in user_codes,
        })
    return result


@app.get("/api/stocks/{code}")
def get_stock_info(code: str):
    """获取单只股票基本信息"""
    dm = get_dm()
    return {
        "code": code,
        "name": dm.get_stock_name(code),
    }


# ==================== 自定义股票管理 ====================

from pydantic import BaseModel


class AddStockRequest(BaseModel):
    code: str


@app.post("/api/stocks/custom/verify")
def verify_stock(req: AddStockRequest):
    """
    验证股票代码是否存在、能否拉取数据。
    返回股票名称和基本信息，验证通过后才能添加。
    """
    code = req.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="股票代码不能为空")

    # 自动补全后缀
    if "." not in code:
        if code.startswith("6"):
            code = f"{code}.XSHG"
        elif code.startswith(("0", "3")):
            code = f"{code}.XSHE"
        else:
            raise HTTPException(status_code=400, detail="无法识别的股票代码格式，请使用如 600519 或 600519.XSHG")

    # 检查是否已在股票池中
    dm = get_dm()
    if code in dm.stock_pool:
        name = dm.get_stock_name(code)
        return {"valid": True, "code": code, "name": name, "exists": True, "message": "该股票已在股票池中"}

    # 尝试从 akshare 获取数据验证
    try:
        tx_code = DataManager._code_to_tx(code)
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=5)).strftime("%Y%m%d")

        df = ak.stock_zh_a_hist_tx(
            symbol=tx_code,
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
            timeout=10.0,
        )
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"无法获取 {code} 的行情数据，请检查代码是否正确")

        # 获取股票名称
        name = dm.get_stock_name(code)

        # 获取最新行情
        latest = df.iloc[-1]
        return {
            "valid": True,
            "code": code,
            "name": name,
            "exists": False,
            "latest_close": float(latest.get("close", 0)) if "close" in df.columns else None,
            "latest_date": str(latest.get("date", "")),
            "message": f"验证成功！{name}({code}) 数据可正常获取",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"验证失败：{str(e)}。请确认代码正确，例如：600519.XSHG 或 000001.XSHE")


@app.post("/api/stocks/custom/add")
def add_custom_stock(req: AddStockRequest):
    """
    添加自定义股票到数据库。
    必须先通过 verify 验证通过后才能添加。
    """
    code = req.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="股票代码不能为空")

    dm = get_dm()

    # 检查是否已在默认池中
    if code in DEFAULT_STOCK_POOL:
        raise HTTPException(status_code=400, detail=f"{code} 已在默认股票池中，无需添加")

    # 验证代码格式并获取名称
    try:
        tx_code = DataManager._code_to_tx(code)
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=5)).strftime("%Y%m%d")
        df = ak.stock_zh_a_hist_tx(
            symbol=tx_code, start_date=start_date, end_date=end_date,
            adjust="qfq", timeout=10.0,
        )
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"无法获取 {code} 的数据")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"数据验证失败：{str(e)}")

    name = dm.get_stock_name(code)
    exchange = code.split(".")[-1] if "." in code else ""

    # 存入数据库
    db = get_db_session()
    try:
        existing = db.query(UserStock).filter_by(code=code).first()
        if existing:
            return {"success": True, "code": code, "name": existing.name, "message": "该股票已在自定义列表中", "is_new": False}

        new_stock = UserStock(code=code, name=name, exchange=exchange)
        db.add(new_stock)
        db.commit()

        # 刷新 DataManager 的股票池缓存
        global _data_manager
        _data_manager = None

        logger.info(f"用户添加自定义股票：{code} {name}")
        return {"success": True, "code": code, "name": name, "message": f"成功添加 {name}({code})", "is_new": True}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"添加失败：{str(e)}")
    finally:
        db.close()


@app.get("/api/stocks/custom/list")
def list_custom_stocks():
    """获取用户自定义股票列表"""
    db = get_db_session()
    try:
        stocks = db.query(UserStock).order_by(UserStock.added_at.desc()).all()
        return {
            "stocks": [
                {"code": s.code, "name": s.name, "exchange": s.exchange, "added_at": s.added_at.isoformat()}
                for s in stocks
            ],
            "count": len(stocks),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.delete("/api/stocks/custom/{code}")
def delete_custom_stock(code: str):
    """删除用户自定义股票"""
    db = get_db_session()
    try:
        stock = db.query(UserStock).filter_by(code=code).first()
        if not stock:
            raise HTTPException(status_code=404, detail=f"未找到自定义股票 {code}")

        name = stock.name
        db.delete(stock)
        db.commit()

        # 刷新 DataManager 缓存
        global _data_manager
        _data_manager = None

        logger.info(f"用户删除自定义股票：{code} {name}")
        return {"success": True, "code": code, "name": name, "message": f"已删除 {name}({code})"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ==================== 行情数据 ====================
@app.get("/api/market/quote/{code}")
def get_stock_quote(
    code: str,
    days: int = Query(default=365, ge=30, le=2000, description="获取天数"),
    use_cache: bool = Query(default=True, description="优先使用本地缓存"),
):
    """
    获取单只股票的日线行情数据（含计算的均线）。
    """
    dm = get_dm()
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

    try:
        # 先尝试从本地加载
        if use_cache:
            filepath = os.path.join(DATA_DIR, f"{code}.csv")
            if os.path.exists(filepath):
                df = pd.read_csv(filepath, dtype={"日期": str})
                df["日期"] = pd.to_datetime(df["日期"])
                df = df.sort_values("日期").reset_index(drop=True)
                cutoff = datetime.now() - timedelta(days=days)
                df = df[df["日期"] >= pd.Timestamp(cutoff)]
                if not df.empty:
                    # 重命名列
                    col_map = {"日期": "date", "开盘": "open", "收盘": "close",
                               "最高": "high", "最低": "low", "成交量": "volume",
                               "成交额": "amount", "涨跌幅": "pct_change"}
                    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
                    for c in ["close", "open", "high", "low"]:
                        if c in df.columns:
                            df[c] = pd.to_numeric(df[c], errors="coerce")
                    return _format_quote_data(df, code, dm)

        # 从 akshare 获取
        tx_code = dm._code_to_tx(code)
        df = ak.stock_zh_a_hist_tx(
            symbol=tx_code,
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
            timeout=10.0,
        )
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"无法获取 {code} 的行情数据")

        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        return _format_quote_data(df, code, dm)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _format_quote_data(df, code, dm):
    """格式化行情数据，添加均线计算"""
    df["ma_fast"] = df["close"].rolling(MA_FAST).mean()
    df["ma_slow"] = df["close"].rolling(MA_SLOW).mean()

    # 金叉死叉
    df["golden_cross"] = (df["ma_fast"] > df["ma_slow"]) & (df["ma_fast"].shift(1) <= df["ma_slow"].shift(1))
    df["death_cross"] = (df["ma_fast"] < df["ma_slow"]) & (df["ma_fast"].shift(1) >= df["ma_slow"].shift(1))

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    change_pct = (latest["close"] - prev["close"]) / prev["close"] * 100 if prev["close"] != 0 else 0

    # 趋势判断
    close_v = float(latest["close"])
    ma_f = float(latest["ma_fast"]) if pd.notna(latest["ma_fast"]) else None
    ma_s = float(latest["ma_slow"]) if pd.notna(latest["ma_slow"]) else None
    trend = _judge_trend(close_v, ma_f, ma_s, df)

    # 构建K线数据
    kline_data = []
    for _, row in df.iterrows():
        kline_data.append({
            "date": row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"]),
            "open": float(row["open"]) if pd.notna(row["open"]) else None,
            "high": float(row["high"]) if pd.notna(row["high"]) else None,
            "low": float(row["low"]) if pd.notna(row["low"]) else None,
            "close": float(row["close"]) if pd.notna(row["close"]) else None,
            "volume": float(row.get("volume", 0)) if pd.notna(row.get("volume", 0)) else 0,
            "ma_fast": float(row["ma_fast"]) if pd.notna(row["ma_fast"]) else None,
            "ma_slow": float(row["ma_slow"]) if pd.notna(row["ma_slow"]) else None,
            "golden_cross": bool(row["golden_cross"]),
            "death_cross": bool(row["death_cross"]),
        })

    return {
        "code": code,
        "name": dm.get_stock_name(code),
        "latest": {
            "date": latest["date"].strftime("%Y-%m-%d") if hasattr(latest["date"], "strftime") else str(latest["date"]),
            "close": close_v,
            "change_pct": round(float(change_pct), 2),
            "ma_fast": round(ma_f, 2) if ma_f else None,
            "ma_slow": round(ma_s, 2) if ma_s else None,
            "trend": trend,
        },
        "kline": kline_data,
        "data_count": len(df),
    }


def _judge_trend(close, ma_fast, ma_slow, df):
    if ma_fast is None or ma_slow is None:
        return {"status": "数据不足", "class": "neutral"}

    if close > ma_fast > ma_slow:
        return {"status": "多头排列", "class": "bullish"}
    elif close < ma_fast < ma_slow:
        return {"status": "空头排列", "class": "bearish"}
    elif ma_fast > ma_slow:
        return {"status": "短期偏多", "class": "bullish"}
    else:
        return {"status": "短期偏空", "class": "bearish"}


# ==================== 行情面板（批量） ====================
@app.get("/api/market/panel")
def get_market_panel(
    limit: int = Query(default=12, ge=1, le=35, description="返回股票数量"),
    use_cache: bool = Query(default=True),
):
    """
    批量获取行情面板数据（股票卡片）。
    """
    dm = get_dm()
    codes = dm.stock_pool[:limit]
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=120)).strftime("%Y%m%d")

    result = []
    for code in codes:
        try:
            if use_cache:
                filepath = os.path.join(DATA_DIR, f"{code}.csv")
                if os.path.exists(filepath):
                    df = pd.read_csv(filepath, dtype={"日期": str})
                    df["日期"] = pd.to_datetime(df["日期"])
                    df = df.sort_values("日期").reset_index(drop=True)
                    cutoff = datetime.now() - timedelta(days=120)
                    df = df[df["日期"] >= pd.Timestamp(cutoff)]
                    df = df.rename(columns={"收盘": "close", "开盘": "open", "最高": "high", "最低": "low"})
                    for c in ["close", "open", "high", "low"]:
                        df[c] = pd.to_numeric(df[c], errors="coerce")
                else:
                    continue
            else:
                tx_code = dm._code_to_tx(code)
                df = ak.stock_zh_a_hist_tx(
                    symbol=tx_code, start_date=start_date, end_date=end_date,
                    adjust="qfq", timeout=10.0,
                )
                if df is None or df.empty:
                    continue
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date").reset_index(drop=True)

            df["ma_fast"] = df["close"].rolling(MA_FAST).mean()
            df["ma_slow"] = df["close"].rolling(MA_SLOW).mean()

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            change_pct = (latest["close"] - prev["close"]) / prev["close"] * 100 if prev["close"] != 0 else 0

            close_v = float(latest["close"])
            ma_f = float(latest["ma_fast"]) if pd.notna(latest["ma_fast"]) else None
            ma_s = float(latest["ma_slow"]) if pd.notna(latest["ma_slow"]) else None
            trend = _judge_trend(close_v, ma_f, ma_s, df)

            date_col = "date" if "date" in df.columns else "日期"
            latest_date = latest[date_col]
            if hasattr(latest_date, "strftime"):
                latest_date = latest_date.strftime("%Y-%m-%d")

            result.append({
                "code": code,
                "name": dm.get_stock_name(code),
                "close": round(close_v, 2),
                "change_pct": round(float(change_pct), 2),
                "ma_fast": round(ma_f, 2) if ma_f else None,
                "ma_slow": round(ma_s, 2) if ma_s else None,
                "trend": trend,
                "latest_date": latest_date,
            })
        except Exception as e:
            logger.warning(f"获取 {code} 行情失败: {e}")
            continue

    # 数据时效性
    if result:
        max_date = max(r["latest_date"] for r in result)
        today = datetime.now()
        days_behind = (today - datetime.strptime(max_date, "%Y-%m-%d")).days
    else:
        max_date = None
        days_behind = None

    return {
        "stocks": result,
        "data_date": max_date,
        "days_behind": days_behind,
        "updated_at": datetime.now().isoformat(),
    }


# ==================== 信号生成 ====================
@app.get("/api/signals/{code}")
def get_signals(code: str, days: int = Query(default=365, ge=30)):
    """
    获取单只股票的双均线交叉信号。
    """
    sg = get_sg()
    dm = get_dm()

    try:
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        tx_code = dm._code_to_tx(code)

        df = ak.stock_zh_a_hist_tx(
            symbol=tx_code, start_date=start_date, end_date=end_date,
            adjust="qfq", timeout=10.0,
        )
        if df is None or df.empty:
            # 回退到本地
            filepath = os.path.join(DATA_DIR, f"{code}.csv")
            if os.path.exists(filepath):
                df = pd.read_csv(filepath, dtype={"日期": str})
                df["日期"] = pd.to_datetime(df["日期"])
                df = df.sort_values("日期").reset_index(drop=True)
                cutoff = datetime.now() - timedelta(days=days)
                df = df[df["日期"] >= pd.Timestamp(cutoff)]
                df = df.rename(columns={"日期": "date", "开盘": "open", "收盘": "close",
                                        "最高": "high", "最低": "low"})
                for c in ["close", "open", "high", "low"]:
                    df[c] = pd.to_numeric(df[c], errors="coerce")
            else:
                raise HTTPException(status_code=404, detail="无数据")

        df["date"] = pd.to_datetime(df["date"]) if "date" in df.columns else pd.to_datetime(df["日期"])
        df = df.sort_values("date").reset_index(drop=True)
        df["ma_fast"] = df["close"].rolling(MA_FAST).mean()
        df["ma_slow"] = df["close"].rolling(MA_SLOW).mean()
        df["golden_cross"] = (df["ma_fast"] > df["ma_slow"]) & (df["ma_fast"].shift(1) <= df["ma_slow"].shift(1))
        df["death_cross"] = (df["ma_fast"] < df["ma_slow"]) & (df["ma_fast"].shift(1) >= df["ma_slow"].shift(1))

        golden = df[df["golden_cross"]][["date", "close", "ma_fast", "ma_slow"]].copy()
        golden.columns = ["date", "close", "ma_fast", "ma_slow"]
        death = df[df["death_cross"]][["date", "close", "ma_fast", "ma_slow"]].copy()
        death.columns = ["date", "close", "ma_fast", "ma_slow"]

        return {
            "code": code,
            "name": dm.get_stock_name(code),
            "golden_crosses": [
                {"date": r["date"].strftime("%Y-%m-%d"), "close": round(float(r["close"]), 2),
                 "ma_fast": round(float(r["ma_fast"]), 2), "ma_slow": round(float(r["ma_slow"]), 2)}
                for _, r in golden.iterrows()
            ],
            "death_crosses": [
                {"date": r["date"].strftime("%Y-%m-%d"), "close": round(float(r["close"]), 2),
                 "ma_fast": round(float(r["ma_fast"]), 2), "ma_slow": round(float(r["ma_slow"]), 2)}
                for _, r in death.iterrows()
            ],
            "latest_signal": {
                "golden": golden["date"].max().strftime("%Y-%m-%d") if not golden.empty else None,
                "death": death["date"].max().strftime("%Y-%m-%d") if not death.empty else None,
            } if not (golden.empty and death.empty) else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 回测 ====================
@app.get("/api/backtest/{code}")
def run_backtest(
    code: str,
    start_date: str = Query(default=None, description="回测起始日期 YYYYMMDD"),
    end_date: str = Query(default=None, description="回测结束日期 YYYYMMDD"),
    initial_cash: float = Query(default=INITIAL_CASH),
    ma_fast: int = Query(default=MA_FAST),
    ma_slow: int = Query(default=MA_SLOW),
):
    """
    对单只股票执行双均线回测。
    """
    if start_date is None:
        start_date = DATA_START_DATE
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")

    be = get_be()
    dm = get_dm()

    try:
        result = be.run_single_backtest(
            code=code,
            start_date=start_date,
            end_date=end_date,
            initial_cash=initial_cash,
            ma_fast=ma_fast,
            ma_slow=ma_slow,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 数据下载 ====================
@app.post("/api/data/download")
def download_data(
    codes: Optional[List[str]] = None,
    start_date: str = Query(default=DATA_START_DATE),
):
    """下载指定股票的历史数据到本地"""
    dm = get_dm()
    if codes is None:
        codes = dm.stock_pool

    success = []
    failed = []
    for code in codes:
        try:
            dm.download_stock_data(code, start_date=start_date)
            success.append(code)
        except Exception as e:
            failed.append({"code": code, "error": str(e)})

    return {
        "success_count": len(success),
        "failed_count": len(failed),
        "success": success,
        "failed": failed,
    }


# ==================== 行情解读（基于规则） ====================
@app.get("/api/market/interpretation/{code}")
def get_interpretation(code: str):
    """生成基于规则的行情解读文本"""
    dm = get_dm()
    try:
        quote = get_stock_quote(code)
        latest = quote["latest"]
        kline = quote["kline"]

        close = latest["close"]
        ma_f = latest["ma_fast"]
        ma_s = latest["ma_slow"]
        date = latest["date"]

        parts = [f"📅 数据日期：{date}"]
        change = latest.get("change_pct", 0)
        parts.append(f"💰 最新收盘价：¥{close:.2f}（当日{'上涨' if change >= 0 else '下跌'}{abs(change):.2f}%）")

        if ma_f is None or ma_s is None:
            parts.append("⚠️ 均线数据不足")
            return {"text": "\n".join(parts)}

        parts.append(f"📊 MA{MA_FAST}：¥{ma_f:.2f}")
        parts.append(f"📊 MA{MA_SLOW}：¥{ma_s:.2f}")

        if close > ma_f > ma_s:
            parts.append(f"✅ 均线呈多头排列，股价位于两条均线之上，属于强势上涨趋势。")
        elif close < ma_f < ma_s:
            parts.append(f"⚠️ 均线呈空头排列，股价位于两条均线之下，属于下跌趋势。建议观望。")
        elif ma_f > ma_s:
            parts.append(f"📌 短期偏多，MA{MA_FAST}仍在MA{MA_SLOW}上方，但股价已跌破短期均线，可能是短期回调。")
        else:
            parts.append(f"📌 短期偏空，MA{MA_FAST}在MA{MA_SLOW}下方。关注MA{MA_FAST}(¥{ma_f:.2f})能否收复。")

        # 最近的金叉/死叉
        golden_dates = [k["date"] for k in kline if k["golden_cross"]]
        death_dates = [k["date"] for k in kline if k["death_cross"]]

        if golden_dates:
            parts.append(f"🔺 最近一次金叉：{golden_dates[-1]}")
        if death_dates:
            parts.append(f"🔻 最近一次死叉：{death_dates[-1]}")

        return {"text": "\n".join(parts), "raw": parts}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 系统状态 ====================
@app.get("/api/system/info")
def system_info():
    """获取系统运行状态"""
    dm = get_dm()
    available = dm.get_available_stocks()
    return {
        "stock_pool_size": len(dm.stock_pool),
        "available_stocks": len(available),
        "data_dir": DATA_DIR,
        "strategy": f"MA{MA_FAST} × MA{MA_SLOW}",
        "initial_cash": INITIAL_CASH,
        "commission_rate": COMMISSION_RATE,
        "slippage": SLIPPAGE,
        "server_time": datetime.now().isoformat(),
    }


# ==================== 启动入口 ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
