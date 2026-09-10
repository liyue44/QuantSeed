"""
薪资计算模块
============
- 输入时薪、休息日、每月加班上限 → 数据持久化到 salary.db
- 日历上点击日期 → 弹窗记录加班小时、标记法定日
- 自动计算正常工资、加班工资、合计
"""

import streamlit as st
import sys
import os
from datetime import date, datetime, timedelta
from calendar import monthrange

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import salary_db
import salary_calc as sc

# ==================== 页面配置 ====================
st.set_page_config(page_title="薪资计算", page_icon="💰", layout="wide")

# ==================== Session State ====================
if "salary_unlocked" not in st.session_state:
    st.session_state.salary_unlocked = False
if "salary_ym" not in st.session_state:
    today = date.today()
    st.session_state.salary_ym = (today.year, today.month)

# ==================== CSS ====================
st.markdown("""
<style>
    .lock-box {
        max-width: 380px;
        margin: 3rem auto;
        padding: 2rem;
        background: rgba(255,255,255,0.04);
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.1);
        text-align: center;
    }
    .lock-icon { font-size: 3rem; display: block; margin-bottom: 0.8rem; }
    .sum-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
    }
    .sum-card .lbl { color:#90a4ae; font-size:0.85rem; }
    .sum-card .val { color:#4fc3f7; font-size:1.6rem; font-weight:700; }
    .sum-card .val.green { color:#66bb6a; }
    .sum-card .val.orange { color:#ffa726; }
    .sum-card .val.pink { color:#ec407a; }

    /* 日历日期按钮美化 */
    div[data-testid="stColumn"] div[data-testid="stButton"] > button {
        min-height: 56px;
        width: 100%;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(255,255,255,0.04);
        color: #e0e0e0;
        font-weight: 600;
        font-size: 0.95rem;
        line-height: 1.3;
        white-space: pre-line;
        padding: 4px 2px;
        transition: transform .12s, box-shadow .12s;
    }
    div[data-testid="stColumn"] div[data-testid="stButton"] > button:hover {
        border-color: #4fc3f7;
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.35);
    }
    /* 休息日按钮 */
    .cal-rest div[data-testid="stColumn"] div[data-testid="stButton"] > button {
        background: rgba(255,167,38,0.12) !important;
        border-color: rgba(255,167,38,0.5) !important;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 密码验证 ====================
if not st.session_state.salary_unlocked:
    st.markdown(
        "<div class='lock-box'>"
        "<span class='lock-icon'>💰</span>"
        "<h2 style='margin:0 0 0.5rem 0;color:#e0e0e0;'>薪资计算程序</h2>"
        "<p style='color:#90a4ae;font-size:0.9rem;'>请输入密码查看</p>"
        "</div>",
        unsafe_allow_html=True)
    pwd = st.text_input("密码", type="password", key="salary_pwd",
                        placeholder="请输入密码", autocomplete="new-password")
    col_enter, _ = st.columns([1, 3])
    with col_enter:
        if st.button("💰 进入", use_container_width=True):
            if pwd == "135246":
                st.session_state.salary_unlocked = True
                st.rerun()
            else:
                st.error("密码错误")
    st.stop()

# ==================== 读取数据 ====================
settings = salary_db.get_settings()
records = salary_db.get_all_records()
custom_holidays_list = salary_db.get_custom_holidays()
custom_holidays_set = set(custom_holidays_list)

year, month = st.session_state.salary_ym
# 系统节假日（允许接口失败，自动降级）
sys_holidays_year = salary_db.get_system_holidays(year)
# 加班窗口可能跨年（1月的窗口落在上一年12月），补充上一年节假日
if month == 1:
    prev = salary_db.get_system_holidays(year - 1)
    sys_holidays = {**prev, **sys_holidays_year}
else:
    sys_holidays = sys_holidays_year

# ==================== 编辑弹窗（st.dialog） ====================
@st.dialog("记录加班")
def edit_dialog(ds: str):
    d_obj = datetime.strptime(ds, "%Y-%m-%d").date()
    dtype = sc.get_day_type(d_obj, settings["rest_days"], custom_holidays_set, sys_holidays)
    type_label = {sc.TYPE_WORKDAY: "工作日（1.5 倍）",
                  sc.TYPE_REST: "休息日（2 倍）",
                  sc.TYPE_HOLIDAY: "法定日（3 倍）"}[dtype]
    st.markdown(f"**{ds}** · 当天类型：{type_label}")

    cur_ot = float(records.get(ds, 0.0))
    new_ot = st.number_input("加班小时", min_value=0.0, max_value=24.0,
                             value=cur_ot, step=0.5, key="dlg_ot")

    is_hol = ds in custom_holidays_set
    mark = st.checkbox("标记为法定日（3 倍）", value=is_hol, key="dlg_hol")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("✅ 保存", type="primary", use_container_width=True):
            salary_db.set_record(ds, new_ot)
            salary_db.set_custom_holiday(ds, mark)
            st.session_state.pop("cal_edit_date", None)
            st.rerun()
    with c2:
        if st.button("🗑️ 清空", use_container_width=True):
            salary_db.set_record(ds, 0)
            salary_db.set_custom_holiday(ds, False)
            st.session_state.pop("cal_edit_date", None)
            st.rerun()
    with c3:
        if st.button("取消", use_container_width=True):
            st.session_state.pop("cal_edit_date", None)
            st.rerun()


# ==================== 标题 + 月份切换 ====================
st.markdown('<h2 style="margin:0 0 0.5rem 0;color:#e0e0e0;">💰 薪资计算程序</h2>',
            unsafe_allow_html=True)

col_prev, col_ym, col_next, _sp = st.columns([1, 2, 1, 4])
with col_prev:
    if st.button("◀ 上月", use_container_width=True):
        y, m = st.session_state.salary_ym
        st.session_state.salary_ym = (y - 1, 12) if m == 1 else (y, m - 1)
        st.rerun()
with col_ym:
    ym_input = st.text_input("年月", value=f"{year}-{month:02d}", key="ym_input",
                             label_visibility="collapsed")
    try:
        parts = ym_input.split("-")
        ny, nm = int(parts[0]), int(parts[1])
        if (ny, nm) != (year, month) and 1 <= nm <= 12:
            st.session_state.salary_ym = (ny, nm)
            st.rerun()
    except Exception:
        pass
with col_next:
    if st.button("下月 ▶", use_container_width=True):
        y, m = st.session_state.salary_ym
        st.session_state.salary_ym = (y + 1, 1) if m == 12 else (y, m + 1)
        st.rerun()

now = datetime.now()
st.caption(f"当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')}")

# ==================== 设置区 ====================
with st.expander("⚙️ 基础设置（时薪 / 休息日 / 每月加班上限）", expanded=(settings["hourly_rate"] <= 0)):
    week_map = {"周一": 1, "周二": 2, "周三": 3, "周四": 4, "周五": 5, "周六": 6, "周日": 0}
    inv_map = {v: k for k, v in week_map.items()}
    default_names = [inv_map[d] for d in settings["rest_days"] if d in inv_map]

    c1, c2, c3 = st.columns(3)
    with c1:
        hourly_rate = st.number_input("时薪（元/小时）", min_value=0.0,
                                      value=float(settings["hourly_rate"]), step=1.0, format="%.2f")
    with c2:
        rest_names = st.multiselect("每周休息日", options=list(week_map.keys()),
                                    default=default_names)
        rest_days = [week_map[n] for n in rest_names]
    with c3:
        monthly_ot_limit = st.number_input("每月加班上限（小时，0=不提醒）", min_value=0.0,
                                           value=float(settings["monthly_ot_limit"]), step=1.0, format="%.1f")

    if st.button("💾 保存设置", type="primary"):
        salary_db.save_settings(hourly_rate, rest_days, monthly_ot_limit)
        st.success("设置已保存")
        st.rerun()

if settings["hourly_rate"] <= 0:
    st.warning("⚠️ 请先在上方「基础设置」中填写时薪并保存。")

# ==================== 计算汇总 ====================
result = sc.calc_all(
    year=year, month=month,
    hourly_rate=settings["hourly_rate"],
    rest_days=settings["rest_days"],
    custom_holidays=custom_holidays_list,
    system_holidays=sys_holidays,
    records=records,
    monthly_ot_limit=settings["monthly_ot_limit"],
)

sc1, sc2, sc3 = st.columns(3)
with sc1:
    st.markdown(
        f"<div class='sum-card'><div class='lbl'>正常工资（{result['normal']['days']} 个工作日 × 8h）</div>"
        f"<div class='val green'>¥ {result['normal']['salary']:,.2f}</div></div>",
        unsafe_allow_html=True)
with sc2:
    st.markdown(
        f"<div class='sum-card'><div class='lbl'>加班工资（窗口 {result['overtime']['windowLabel']}）</div>"
        f"<div class='val orange'>¥ {result['overtime']['totalOTSalary']:,.2f}</div></div>",
        unsafe_allow_html=True)
with sc3:
    st.markdown(
        f"<div class='sum-card'><div class='lbl'>合计收入</div>"
        f"<div class='val'>¥ {result['total_income']:,.2f}</div></div>",
        unsafe_allow_html=True)

od = result["overtime"]["detail"]
st.markdown("**加班明细**")
d1, d2, d3, d4 = st.columns(4)
d1.metric(od["dailyOT"]["label"], f"{od['dailyOT']['hours']}h", f"¥{od['dailyOT']['salary']:,.2f}")
d2.metric(od["restOT"]["label"], f"{od['restOT']['hours']}h", f"¥{od['restOT']['salary']:,.2f}")
d3.metric(od["holidayOT"]["label"], f"{od['holidayOT']['hours']}h", f"¥{od['holidayOT']['salary']:,.2f}")
d4.metric("加班总时长", f"{result['overtime']['totalOTHours']}h")

limit = settings["monthly_ot_limit"]
if limit > 0:
    used = result["overtime"]["totalOTHours"]
    pct = min(used / limit, 1.0) if limit else 0
    if used > limit:
        st.error(f"🚨 本月加班 {used}h 已超过上限 {limit}h！")
    elif used >= limit * 0.8:
        st.warning(f"⚠️ 本月加班 {used}h，已接近上限 {limit}h。")
    else:
        st.info(f"📊 本月加班 {used}h / 上限 {limit}h。")
    st.progress(pct)

# ==================== 日历 ====================
st.markdown("---")
st.markdown("### 📅 加班日历")
st.caption("点击日期即可弹窗记录加班；弹窗内可标记法定日（3 倍）。")

_cal_start, _cal_end = sc.calc_calendar_range(year, month)

# 图例
st.markdown(
    "<div style='display:flex;gap:18px;font-size:0.8rem;color:#90a4ae;margin-bottom:8px;'>"
    "<span>⬜ 工作日 1.5x</span>"
    "<span style='color:#ffa726;'>🟧 休息日 2x</span>"
    "<span style='color:#ec407a;'>🟥 法定日 3x</span>"
    "</div>", unsafe_allow_html=True)

# 星期表头
_headers = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
_hcols = st.columns(7)
for i, h in enumerate(_headers):
    _hcols[i].markdown(
        f"<div style='text-align:center;color:#90a4ae;font-weight:600;padding:2px 0;'>{h}</div>",
        unsafe_allow_html=True)

# 生成日期网格
_all_days = []
_d = _cal_start
while _d <= _cal_end:
    _all_days.append(_d)
    _d += timedelta(days=1)

_lead = _cal_start.weekday()  # 周一=0
_grid = [None] * _lead + _all_days

for wi in range((len(_grid) + 6) // 7):
    row_days = _grid[wi * 7: wi * 7 + 7]
    cols = st.columns(7)
    for ci, d in enumerate(row_days):
        with cols[ci]:
            if d is None:
                st.markdown("&nbsp;", unsafe_allow_html=True)
                continue
            ds = d.strftime("%Y-%m-%d")
            dtype = sc.get_day_type(d, settings["rest_days"], custom_holidays_set, sys_holidays)
            ot = records.get(ds, 0)
            in_month = (d.year == year and d.month == month)

            # 按钮文字：日期 + 加班标记
            label = f"{d.day}"
            if not in_month:
                label = f"{d.month}月{d.day}"
            if ot > 0:
                label += f"\n🔵{ot}h"

            # 用 emoji 前缀区分类型（按钮内部不好加边框色，用符号提示）
            if dtype == sc.TYPE_HOLIDAY:
                prefix = "🔴"
            elif dtype == sc.TYPE_REST:
                prefix = "🟠"
            else:
                prefix = ""
            btn_label = f"{prefix}{label}"

            if st.button(btn_label, key=f"cal_{ds}", use_container_width=True):
                st.session_state["cal_edit_date"] = ds
                st.rerun()

# 打开弹窗
if st.session_state.get("cal_edit_date"):
    edit_dialog(st.session_state["cal_edit_date"])

# ==================== 每周加班统计 ====================
st.markdown("---")
st.markdown("### 📊 每周加班统计")
weekly = sc.calc_weekly_ot(year, month, settings["rest_days"], custom_holidays_set, sys_holidays, records)
if weekly:
    import pandas as pd
    df = pd.DataFrame([{
        "周次": f"第{w['week_no']}周",
        "日期范围": w["range"],
        "加班时长(h)": w["hours"],
        "上限(h)": w["limit"],
        "剩余(h)": w["remaining"],
    } for w in weekly])
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.caption("本月暂无加班记录。")

# ==================== 退出 ====================
st.markdown("---")
col_exit, _ = st.columns([1, 5])
with col_exit:
    if st.button("🚪 退出", use_container_width=True):
        st.session_state.salary_unlocked = False
        st.rerun()
