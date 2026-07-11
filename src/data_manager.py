"""
数据管理模块 - data_manager.py
============================
负责A股日线数据的下载、本地存储、加载与更新。
第二阶段扩展点：可将数据源切换为实时行情API（如Tushare Pro），
或接入数据库（SQLite/PostgreSQL）替代CSV文件存储。
"""

import os
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional, Dict

import akshare as ak

from config import (
    DATA_DIR, DATA_START_DATE, DEFAULT_STOCK_POOL, STOCK_LIST_FILE,
    setup_logging, ensure_dirs
)

# 初始化日志
logger = setup_logging("DataManager")


class DataManager:
    """
    A股日线数据管理器

    职责：
    1. 批量下载股票日线数据（akshare）
    2. 本地CSV存储与增量更新（断点续传）
    3. 将数据转换为backtrader兼容格式

    第二阶段扩展点：
    - 可增加实时行情订阅接口
    - 可增加数据库读写层，替代CSV文件
    - 可增加数据质量校验（异常价格检测、复权校验）
    """

    # backtrader 所需的列名映射
    BT_COLUMN_MAP = {
        "日期": "datetime",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
    }

    # akshare stock_zh_a_hist 返回的所有字段
    ALL_FIELDS = [
        "日期", "开盘", "收盘", "最高", "最低", "成交量",
        "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"
    ]

    def __init__(self, stock_pool: Optional[List[str]] = None):
        """
        初始化数据管理器

        Args:
            stock_pool: 股票代码列表，默认使用config中的DEFAULT_STOCK_POOL
        """
        ensure_dirs()
        self.stock_pool = stock_pool or self._load_stock_pool()
        self._name_cache: Dict[str, str] = {}  # 股票名称缓存，避免重复API调用
        logger.info(f"DataManager初始化完成，股票池共 {len(self.stock_pool)} 只股票")

    def _load_stock_pool(self) -> List[str]:
        """
        加载股票池：优先从本地CSV文件读取，不存在则使用默认列表并自动保存。

        CSV格式：每行一个股票代码，如 000001.XSHE
        第二阶段扩展点：可从数据库读取、或通过API动态获取成分股列表。
        """
        if os.path.exists(STOCK_LIST_FILE):
            try:
                df = pd.read_csv(STOCK_LIST_FILE, dtype=str)
                if "code" in df.columns:
                    codes = df["code"].str.strip().tolist()
                else:
                    codes = df.iloc[:, 0].str.strip().tolist()
                logger.info(f"从文件加载股票池：{len(codes)} 只股票")
                return codes
            except Exception as e:
                logger.warning(f"读取股票池文件失败：{e}，使用默认列表")

        # 保存默认股票池到文件
        df = pd.DataFrame({"code": DEFAULT_STOCK_POOL})
        os.makedirs(os.path.dirname(STOCK_LIST_FILE), exist_ok=True)
        df.to_csv(STOCK_LIST_FILE, index=False, encoding="utf-8-sig")
        logger.info(f"已创建默认股票池文件：{STOCK_LIST_FILE}")
        return DEFAULT_STOCK_POOL

    @staticmethod
    def _code_to_akshare(code: str) -> str:
        """
        将带后缀的代码转换为akshare需要的纯数字格式（东方财富源）
        如 '000001.XSHE' -> '000001'
        """
        return code.split(".")[0]

    @staticmethod
    def _code_to_tx(code: str) -> str:
        """
        将带后缀的代码转换为腾讯数据源格式
        如 '000001.XSHE' -> 'sz000001'
        如 '600000.XSHG' -> 'sh600000'
        """
        pure_code = code.split(".")[0]
        exchange = code.split(".")[-1] if "." in code else ""
        if exchange.upper() == "XSHG":
            return f"sh{pure_code}"
        elif exchange.upper() == "XSHE":
            return f"sz{pure_code}"
        else:
            # 根据代码前缀判断：6开头是上海，0/3开头是深圳
            if pure_code.startswith("6"):
                return f"sh{pure_code}"
            else:
                return f"sz{pure_code}"

    @staticmethod
    def _code_to_exchange(code: str) -> str:
        """从代码中提取交易所后缀"""
        return code.split(".")[-1] if "." in code else ""

    def _get_csv_path(self, code: str) -> str:
        """获取指定股票的本地CSV文件路径"""
        return os.path.join(DATA_DIR, f"{code}.csv")

    def _get_latest_date(self, code: str) -> Optional[str]:
        """
        获取本地CSV文件中最新的日期（用于断点续传）

        Returns:
            最新日期字符串 'YYYYMMDD'，如果文件不存在则返回None
        """
        filepath = self._get_csv_path(code)
        if not os.path.exists(filepath):
            return None
        try:
            df = pd.read_csv(filepath, dtype={"日期": str})
            if df.empty:
                return None
            dates = pd.to_datetime(df["日期"])
            latest = dates.max().strftime("%Y%m%d")
            return latest
        except Exception as e:
            logger.warning(f"读取 {code} 最新日期失败：{e}")
            return None

    def download_data(
        self,
        codes: Optional[List[str]] = None,
        start_date: str = DATA_START_DATE,
        end_date: Optional[str] = None,
        sleep_interval: float = 1.0,
        max_retries: int = 3,
    ) -> Dict[str, bool]:
        """
        批量下载股票日线数据（支持断点续传+重试）

        Args:
            codes: 要下载的股票代码列表，默认全部
            start_date: 数据起始日期
            end_date: 数据结束日期，默认今天
            sleep_interval: 每次请求间隔秒数（避免被封IP）
            max_retries: 单只股票最大重试次数

        Returns:
            {code: success} 字典，记录每只股票的下载结果
        """
        codes = codes or self.stock_pool
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        results = {}
        total = len(codes)
        logger.info(f"开始批量下载数据，共 {total} 只股票，日期范围：{start_date} ~ {end_date}")

        for idx, code in enumerate(codes, 1):
            # 断点续传：检查本地最新日期
            latest_date = self._get_latest_date(code)
            if latest_date and latest_date >= end_date:
                logger.debug(f"[{idx}/{total}] {code} 数据已是最新，跳过")
                results[code] = True
                continue

            # 增量下载：从本地最新日期的下一天开始
            actual_start = start_date
            if latest_date:
                latest_dt = datetime.strptime(latest_date, "%Y%m%d")
                actual_start = (latest_dt + timedelta(days=1)).strftime("%Y%m%d")
                if actual_start >= end_date:
                    logger.debug(f"[{idx}/{total}] {code} 无需更新")
                    results[code] = True
                    continue

            # 带重试的下载逻辑
            success = False
            last_error = None
            for attempt in range(max_retries):
                try:
                    tx_code = self._code_to_tx(code)
                    # 优先使用腾讯数据源（stock_zh_a_hist_tx），东方财富源在某些网络环境下不通
                    df_new = ak.stock_zh_a_hist_tx(
                        symbol=tx_code,
                        start_date=actual_start,
                        end_date=end_date,
                        adjust="qfq",
                        timeout=15.0,
                    )

                    if df_new is None or df_new.empty:
                        logger.debug(f"[{idx}/{total}] {code} 无新数据")
                        success = True
                        break

                    # 腾讯数据源字段标准化：date→日期, open→开盘, close→收盘, high→最高, low→最低, amount→成交额
                    df_new = self._normalize_columns_tx(df_new)

                    # 与本地已有数据合并
                    filepath = self._get_csv_path(code)
                    if os.path.exists(filepath) and latest_date:
                        df_old = pd.read_csv(filepath, dtype={"日期": str})
                        df_combined = pd.concat([df_old, df_new], ignore_index=True)
                        df_combined = df_combined.drop_duplicates(subset=["日期"], keep="last")
                        df_combined = df_combined.sort_values("日期").reset_index(drop=True)
                    else:
                        df_combined = df_new

                    # 保存
                    self._save_to_csv(code, df_combined)
                    logger.info(f"[{idx}/{total}] {code} 下载成功，新增 {len(df_new)} 条记录")
                    success = True
                    break

                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        wait = (attempt + 1) * 3  # 3s, 6s, 9s 指数退避
                        logger.warning(
                            f"[{idx}/{total}] {code} 第{attempt+1}次失败，{wait}秒后重试: {e}"
                        )
                        time.sleep(wait)
                    else:
                        logger.error(f"[{idx}/{total}] {code} 下载失败(已重试{max_retries}次): {e}")

            results[code] = success
            if not success:
                logger.error(f"[{idx}/{total}] {code} 最终失败: {last_error}")

            # 请求间隔
            if idx < total:
                time.sleep(sleep_interval)

        success_count = sum(1 for v in results.values() if v)
        logger.info(f"数据下载完成：成功 {success_count}/{total}")
        return results

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化akshare东方财富源返回的列名，确保与预期字段一致。
        """
        col_aliases = {
            "日期": "日期",
            "date": "日期",
            "开盘": "开盘",
            "open": "开盘",
            "收盘": "收盘",
            "close": "收盘",
            "最高": "最高",
            "high": "最高",
            "最低": "最低",
            "low": "最低",
            "成交量": "成交量",
            "volume": "成交量",
            "成交额": "成交额",
            "振幅": "振幅",
            "涨跌幅": "涨跌幅",
            "涨跌额": "涨跌额",
            "换手率": "换手率",
        }

        rename_map = {}
        for col in df.columns:
            if col in col_aliases:
                standard = col_aliases[col]
                if col != standard:
                    rename_map[col] = standard

        if rename_map:
            df = df.rename(columns=rename_map)
        return df

    def _normalize_columns_tx(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化腾讯数据源（stock_zh_a_hist_tx）返回的列名。
        腾讯源返回字段：date, open, close, high, low, amount
        需要映射为中文标准字段，并补全缺失字段。
        """
        # 列名映射
        tx_map = {
            "date": "日期",
            "open": "开盘",
            "close": "收盘",
            "high": "最高",
            "low": "最低",
            "amount": "成交额",
        }
        df = df.rename(columns=tx_map)

        # 腾讯源不返回成交量、振幅、涨跌幅等，需要补NaN
        for field in ["成交量", "振幅", "涨跌幅", "涨跌额", "换手率"]:
            if field not in df.columns:
                df[field] = np.nan

        # 如果成交额列存在，尝试从成交额估算成交量（不精确但backtrader需要）
        if "成交额" in df.columns and "成交量" in df.columns:
            # 用成交额/收盘价 估算成交量（单位：手 = 成交额/收盘价/100）
            df["估算成交量"] = df["成交额"] / df["收盘"] / 100
            # 如果原始成交量全为NaN，用估算值填充
            if df["成交量"].isna().all():
                df["成交量"] = df["估算成交量"]
            df = df.drop(columns=["估算成交量"])

        return df

    def _save_to_csv(self, code: str, df: pd.DataFrame):
        """
        保存数据到本地CSV文件

        Args:
            code: 股票代码（带后缀）
            df: 标准化后的DataFrame
        """
        filepath = self._get_csv_path(code)
        # 确保需要的字段都存在，缺失的填充NaN
        for field in self.ALL_FIELDS:
            if field not in df.columns:
                df[field] = np.nan
                logger.debug(f"{code} 缺少字段 {field}，已填充NaN")

        # 只保留需要的字段
        df = df[self.ALL_FIELDS].copy()
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        logger.debug(f"已保存：{filepath}，共 {len(df)} 条")

    def load_data_for_backtrader(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """
        加载指定股票的数据，转换为backtrader兼容格式。

        Args:
            code: 股票代码（带后缀）
            start_date: 起始日期 'YYYY-MM-DD' 或 'YYYYMMDD'
            end_date: 结束日期 'YYYY-MM-DD' 或 'YYYYMMDD'

        Returns:
            backtrader格式的DataFrame，列名：datetime, open, high, low, close, volume
            如果文件不存在返回None

        第二阶段扩展点：可改为从数据库读取，或接入实时行情源。
        """
        filepath = self._get_csv_path(code)
        if not os.path.exists(filepath):
            logger.warning(f"数据文件不存在：{filepath}")
            return None

        try:
            df = pd.read_csv(filepath, dtype={"日期": str})

            # 只取backtrader需要的列并重命名
            # BT_COLUMN_MAP: {"日期": "datetime", "开盘": "open", ...}
            # 先筛选CSV中存在的中文列名，再重命名为英文
            chinese_cols = [c for c in self.BT_COLUMN_MAP.keys() if c in df.columns]
            df_bt = df[chinese_cols].rename(columns=self.BT_COLUMN_MAP)

            # 确保datetime列是datetime类型，并设为索引
            df_bt["datetime"] = pd.to_datetime(df_bt["datetime"])
            df_bt = df_bt.set_index("datetime")
            df_bt = df_bt.sort_index()

            # 处理缺失值：前向填充（停牌日延续前一日价格）
            # backtrader会自动处理NaN，但填充后回测更连续
            df_bt = df_bt.ffill()

            # 按日期范围过滤
            if start_date:
                start_dt = pd.to_datetime(start_date.replace("-", "")[:8], format="%Y%m%d")
                df_bt = df_bt[df_bt.index >= start_dt]
            if end_date:
                end_dt = pd.to_datetime(end_date.replace("-", "")[:8], format="%Y%m%d")
                df_bt = df_bt[df_bt.index <= end_dt]

            # 确保数值列类型正确
            for col in ["open", "high", "low", "close", "volume"]:
                if col in df_bt.columns:
                    df_bt[col] = pd.to_numeric(df_bt[col], errors="coerce")

            return df_bt

        except Exception as e:
            logger.error(f"加载 {code} 数据失败：{e}")
            return None

    def load_all_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        批量加载股票池所有数据

        Returns:
            {code: DataFrame} 字典
        """
        data = {}
        for code in self.stock_pool:
            df = self.load_data_for_backtrader(code, start_date, end_date)
            if df is not None and not df.empty:
                data[code] = df
        logger.info(f"加载了 {len(data)}/{len(self.stock_pool)} 只股票的数据")
        return data

    def get_stock_name(self, code: str) -> str:
        """通过akshare获取股票名称（带缓存）"""
        pure_code = self._code_to_akshare(code)

        # 先从缓存查找
        if pure_code in self._name_cache:
            return self._name_cache[pure_code]

        try:
            # 首次调用时批量加载所有股票名称到缓存
            if len(self._name_cache) == 0:
                info_df = ak.stock_info_a_code_name()
                for _, row in info_df.iterrows():
                    self._name_cache[str(row["code"])] = str(row["name"])
                logger.info(f"已加载 {len(self._name_cache)} 条股票名称")

            if pure_code in self._name_cache:
                return self._name_cache[pure_code]
        except Exception as e:
            logger.warning(f"获取股票名称失败：{e}")

        return pure_code  # 失败则返回代码本身

    def update_all(self) -> Dict[str, bool]:
        """
        一键更新股票池中所有股票的数据至最新交易日。
        供Web界面"更新数据"按钮调用。

        Returns:
            {code: success} 字典
        """
        logger.info("=" * 50)
        logger.info("开始全量数据更新")
        logger.info("=" * 50)
        results = self.download_data(codes=self.stock_pool)
        logger.info("全量数据更新完成")
        return results

    def get_available_stocks(self) -> List[str]:
        """
        获取本地已下载数据的股票列表

        Returns:
            已下载数据的股票代码列表
        """
        available = []
        for code in self.stock_pool:
            filepath = self._get_csv_path(code)
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                available.append(code)
        return available

    def get_latest_prices(self) -> pd.DataFrame:
        """
        获取股票池中所有股票的最新收盘价和基本信息。
        用于信号生成模块。

        Returns:
            DataFrame包含：code, name, latest_date, close, ma20, ma60 等
        """
        records = []
        for code in self.stock_pool:
            filepath = self._get_csv_path(code)
            if not os.path.exists(filepath):
                continue
            try:
                df = pd.read_csv(filepath, dtype={"日期": str})
                if df.empty:
                    continue
                df["日期"] = pd.to_datetime(df["日期"])
                df = df.sort_values("日期")

                latest = df.iloc[-1]
                records.append({
                    "code": code,
                    "pure_code": self._code_to_akshare(code),
                    "latest_date": latest["日期"],
                    "close": float(latest["收盘"]) if pd.notna(latest["收盘"]) else np.nan,
                    "open": float(latest["开盘"]) if pd.notna(latest["开盘"]) else np.nan,
                    "high": float(latest["最高"]) if pd.notna(latest["最高"]) else np.nan,
                    "low": float(latest["最低"]) if pd.notna(latest["最低"]) else np.nan,
                    "volume": float(latest["成交量"]) if pd.notna(latest["成交量"]) else np.nan,
                })
            except Exception as e:
                logger.warning(f"读取 {code} 最新价格失败：{e}")

        return pd.DataFrame(records)


# ==================== 模块自测 ====================
if __name__ == "__main__":
    dm = DataManager()
    # 测试下载单只股票
    dm.download_data(codes=["000001.XSHE"])
    # 测试加载数据
    df = dm.load_data_for_backtrader("000001.XSHE")
    if df is not None:
        print(df.head())
        print(f"\n数据范围：{df.index[0]} ~ {df.index[-1]}")
        print(f"总行数：{len(df)}")
