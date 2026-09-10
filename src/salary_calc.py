"""
薪资计算核心逻辑
================
严格对齐《薪资计算规则说明》：
- 正常工资：当月1号~今天（过去月份=整月，未来月份=0），普通工作日 × 8h × 时薪
- 加班工资：加班窗口 = 上月26 ~ 本月25，按当天类型 × 倍数
- 类型优先级：手动法定日(3x) > 系统节假日(3x) > 休息日(2x) > 工作日(1x/1.5x)
"""

from datetime import datetime, timedelta, date
from calendar import monthrange
from typing import Dict, List, Optional

# 类型常量
TYPE_WORKDAY = "workday"
TYPE_REST = "rest"
TYPE_HOLIDAY = "holiday"

# 倍数
RATE_NORMAL = 1.0
RATE_WORKDAY_OT = 1.5
RATE_REST_OT = 2.0
RATE_HOLIDAY_OT = 3.0

# 平日固定工时
NORMAL_HOURS_PER_DAY = 8.0


def _parse(d: str) -> date:
    return datetime.strptime(d, "%Y-%m-%d").date()


def _fmt(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def get_day_type(
    d: date,
    rest_days: List[int],
    custom_holidays: set,
    system_holidays: Dict[str, dict],
) -> str:
    """
    判断某天类型，优先级：手动法定日 > 系统节假日 > 休息日 > 工作日
    rest_days 用 JS getDay() 语义：0=周日 ... 6=周六
    """
    ds = _fmt(d)
    if ds in custom_holidays:
        return TYPE_HOLIDAY
    md = d.strftime("%m-%d")
    if md in (system_holidays or {}):
        return TYPE_HOLIDAY
    # Python weekday(): 周一=0 ... 周日=6  → 转换成 JS getDay(): 周日=0 ... 周六=6
    js_dow = (d.weekday() + 1) % 7
    if js_dow in rest_days:
        return TYPE_REST
    return TYPE_WORKDAY


def get_ot_window(year: int, month: int):
    """加班窗口：上月26 ~ 本月25，返回 (start_date, end_date)"""
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    start = date(prev_year, prev_month, 26)
    end = date(year, month, 25)
    return start, end


def get_normal_range(year: int, month: int, today: Optional[date] = None):
    """
    正常工资统计范围：
    - 未来月份 → (None, None) 表示 0
    - 过去月份 → 整月 1 号 ~ 月末
    - 当月     → 1 号 ~ 今天
    """
    if today is None:
        today = date.today()
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])
    view_month = (year, month)
    cur_month = (today.year, today.month)

    if view_month > cur_month:
        return None, None  # 未来月份
    if view_month < cur_month:
        return first, last  # 过去月份：整月
    return first, today  # 当月：到今天


def calc_normal_salary(
    year: int,
    month: int,
    hourly_rate: float,
    rest_days: List[int],
    custom_holidays: set,
    system_holidays: Dict[str, dict],
    today: Optional[date] = None,
) -> Dict:
    """计算正常工资"""
    start, end = get_normal_range(year, month, today)
    if start is None:
        return {"hours": 0.0, "salary": 0.0, "days": 0, "workdays": []}
    if hourly_rate <= 0:
        return {"hours": 0.0, "salary": 0.0, "days": 0, "workdays": []}

    workdays = []
    d = start
    while d <= end:
        if get_day_type(d, rest_days, custom_holidays, system_holidays) == TYPE_WORKDAY:
            workdays.append(_fmt(d))
        d += timedelta(days=1)

    days = len(workdays)
    hours = days * NORMAL_HOURS_PER_DAY
    salary = hours * hourly_rate * RATE_NORMAL
    return {"hours": round(hours, 1), "salary": round(salary, 2), "days": days, "workdays": workdays}


def calc_overtime(
    year: int,
    month: int,
    hourly_rate: float,
    rest_days: List[int],
    custom_holidays: set,
    system_holidays: Dict[str, dict],
    records: Dict[str, float],
    monthly_ot_limit: float = 0.0,
) -> Dict:
    """计算加班工资（窗口 上月26 ~ 本月25）"""
    start, end = get_ot_window(year, month)
    window_label = f"{start.month}/{start.day} ~ {end.month}/{end.day}"

    daily_h = daily_s = 0.0
    rest_h = rest_s = 0.0
    hol_h = hol_s = 0.0

    for ds, hours in (records or {}).items():
        try:
            d = _parse(ds)
        except Exception:
            continue
        if not (start <= d <= end):
            continue
        if hours <= 0:
            continue
        t = get_day_type(d, rest_days, custom_holidays, system_holidays)
        if t == TYPE_HOLIDAY:
            hol_h += hours
            hol_s += hours * RATE_HOLIDAY_OT * hourly_rate
        elif t == TYPE_REST:
            rest_h += hours
            rest_s += hours * RATE_REST_OT * hourly_rate
        else:
            daily_h += hours
            daily_s += hours * RATE_WORKDAY_OT * hourly_rate

    total_h = daily_h + rest_h + hol_h
    total_s = daily_s + rest_s + hol_s
    return {
        "windowLabel": window_label,
        "totalOTHours": round(total_h, 1),
        "totalOTSalary": round(total_s, 2),
        "detail": {
            "dailyOT": {"label": "日常加班(1.5x)", "hours": round(daily_h, 1), "salary": round(daily_s, 2)},
            "restOT": {"label": "休息日加班(2x)", "hours": round(rest_h, 1), "salary": round(rest_s, 2)},
            "holidayOT": {"label": "节假日加班(3x)", "hours": round(hol_h, 1), "salary": round(hol_s, 2)},
        },
        "overtimeLimit": monthly_ot_limit,
    }


def calc_calendar_range(year: int, month: int):
    """
    日历范围：从加班窗口起始日所在周的周一，到窗口结束日所在周的周日
    返回 (cal_start, cal_end)
    """
    ws, we = get_ot_window(year, month)
    cal_start = ws - timedelta(days=ws.weekday())          # 所在周周一
    cal_end = we + timedelta(days=(6 - we.weekday()))       # 所在周周日
    return cal_start, cal_end


def calc_weekly_ot(
    year: int,
    month: int,
    rest_days: List[int],
    custom_holidays: set,
    system_holidays: Dict[str, dict],
    records: Dict[str, float],
    weekly_limit: float = 20.0,
) -> List[Dict]:
    """每周加班统计（按当月日期分组，周一~周日）"""
    days_in_month = monthrange(year, month)[1]
    # 按周分组
    weeks = {}
    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        monday = d - timedelta(days=d.weekday())
        weeks.setdefault(monday, []).append(d)

    result = []
    for i, (monday, days) in enumerate(sorted(weeks.items()), 1):
        sunday = monday + timedelta(days=6)
        hours = 0.0
        for d in days:
            ds = _fmt(d)
            if ds in (records or {}) and records[ds] > 0:
                hours += records[ds]
        result.append({
            "week_no": i,
            "range": f"{monday.month}/{monday.day} ~ {sunday.month}/{sunday.day}",
            "hours": round(hours, 1),
            "limit": weekly_limit,
            "remaining": round(max(weekly_limit - hours, 0), 1),
        })
    return result


def calc_all(
    year: int,
    month: int,
    hourly_rate: float,
    rest_days: List[int],
    custom_holidays: List[str],
    system_holidays: Dict[str, dict],
    records: Dict[str, float],
    monthly_ot_limit: float = 0.0,
    today: Optional[date] = None,
) -> Dict:
    """汇总计算"""
    custom_set = set(custom_holidays or [])
    normal = calc_normal_salary(year, month, hourly_rate, rest_days, custom_set, system_holidays, today)
    overtime = calc_overtime(year, month, hourly_rate, rest_days, custom_set, system_holidays, records, monthly_ot_limit)
    total = round(normal["salary"] + overtime["totalOTSalary"], 2)
    return {
        "normal": normal,
        "overtime": overtime,
        "total_income": total,
    }
