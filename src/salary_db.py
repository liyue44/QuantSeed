"""
薪资计算数据库操作
==================
存储内容：
- settings: 时薪、休息日、每月加班上限
- records: 加班记录 {"YYYY-MM-DD": 加班小时数}
- custom_holidays: 手动标记的法定日 {"YYYY-MM-DD": true}
- balance: 已领工资余额（可选，用于累计）
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, List, Dict

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "salary.db")


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化表结构"""
    conn = _get_conn()
    cur = conn.cursor()
    # 设置表（单行配置，id 固定为 1）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS salary_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            hourly_rate REAL NOT NULL DEFAULT 0,
            rest_days TEXT NOT NULL DEFAULT '[3,4]',
            monthly_ot_limit REAL NOT NULL DEFAULT 0,
            updated_at TEXT
        )
    """)
    # 加班记录表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS salary_records (
            date TEXT PRIMARY KEY,
            ot_hours REAL NOT NULL DEFAULT 0,
            updated_at TEXT
        )
    """)
    # 手动法定日表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS salary_custom_holidays (
            date TEXT PRIMARY KEY,
            updated_at TEXT
        )
    """)
    # 初始化设置行
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("SELECT id FROM salary_settings WHERE id = 1")
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO salary_settings (id, hourly_rate, rest_days, monthly_ot_limit, updated_at) "
            "VALUES (1, 0, '[3,4]', 0, ?)",
            (now,)
        )
    conn.commit()
    conn.close()


def get_settings() -> Dict:
    """读取设置"""
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM salary_settings WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"hourly_rate": 0.0, "rest_days": [3, 4], "monthly_ot_limit": 0.0}
    try:
        rest_days = json.loads(row["rest_days"])
    except Exception:
        rest_days = [3, 4]
    return {
        "hourly_rate": row["hourly_rate"],
        "rest_days": rest_days,
        "monthly_ot_limit": row["monthly_ot_limit"],
    }


def save_settings(hourly_rate: float, rest_days: List[int], monthly_ot_limit: float):
    """保存设置"""
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "UPDATE salary_settings SET hourly_rate=?, rest_days=?, monthly_ot_limit=?, updated_at=? WHERE id=1",
        (float(hourly_rate), json.dumps(sorted(rest_days)), float(monthly_ot_limit), now)
    )
    conn.commit()
    conn.close()


def get_all_records() -> Dict[str, float]:
    """读取所有加班记录 {date: hours}"""
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT date, ot_hours FROM salary_records WHERE ot_hours > 0")
    rows = cur.fetchall()
    conn.close()
    return {r["date"]: r["ot_hours"] for r in rows}


def set_record(date: str, hours: float):
    """写入/更新某天加班记录（0 视为删除）"""
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if hours <= 0:
        cur.execute("DELETE FROM salary_records WHERE date = ?", (date,))
    else:
        cur.execute(
            "INSERT INTO salary_records (date, ot_hours, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(date) DO UPDATE SET ot_hours=excluded.ot_hours, updated_at=excluded.updated_at",
            (date, float(hours), now)
        )
    conn.commit()
    conn.close()


def get_custom_holidays() -> List[str]:
    """读取所有手动法定日"""
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT date FROM salary_custom_holidays")
    rows = cur.fetchall()
    conn.close()
    return [r["date"] for r in rows]


def set_custom_holiday(date: str, is_holiday: bool):
    """标记/取消标记某天为法定日"""
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if is_holiday:
        cur.execute(
            "INSERT OR REPLACE INTO salary_custom_holidays (date, updated_at) VALUES (?, ?)",
            (date, now)
        )
    else:
        cur.execute("DELETE FROM salary_custom_holidays WHERE date = ?", (date,))
    conn.commit()
    conn.close()


# ==================== 节假日接口（timor.tech） ====================
_HOLIDAY_CACHE: Dict[int, Dict[str, dict]] = {}


def get_system_holidays(year: int) -> Dict[str, dict]:
    """
    获取系统法定节假日 {"MM-DD": {"name": ..., "wage": ...}}
    接口失败时返回空 dict（降级，不影响核心计算）
    """
    if year in _HOLIDAY_CACHE:
        return _HOLIDAY_CACHE[year]
    try:
        import urllib.request
        url = f"https://timor.tech/api/holiday/year/{year}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        result = {}
        holidays = (data or {}).get("holiday", {}) or {}
        for md, info in holidays.items():
            # 只取真正的节假日（type.type==1），排班补班的忽略
            if isinstance(info, dict) and info.get("holiday", True) and info.get("type", {}).get("type") == 1:
                result[md] = info
        _HOLIDAY_CACHE[year] = result
        return result
    except Exception:
        _HOLIDAY_CACHE[year] = {}
        return {}
