import streamlit as st
import pandas as pd
from datetime import datetime
import os
import re

# ==========================================
# ⚙️ 配置区域
# ==========================================
SCHEDULE_FILE = '选课教室及教师安排.csv'
STUDENTS_FILE = '2025-2026 ECA 选课总表.csv'
DB_FILE = 'eca_daily_logs.csv'
ADMIN_PASSWORD = "8888"

st.set_page_config(page_title="ECA 智能追踪系统", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# 🛠️ 1. 强力读取模块
# ==========================================
def smart_read(filename):
    if not os.path.exists(filename): return pd.DataFrame(), f"❌ 找不到文件：{filename}"
    for enc in ['utf-8-sig', 'gbk', 'utf-16']:
        try:
            df = pd.read_csv(filename, encoding=enc, engine='python', on_bad_lines='skip', dtype=str)
            if len(df.columns) < 2: continue
            return df, None
        except: continue
    return pd.DataFrame(), f"❌ 无法读取 {filename}"

# ==========================================
# 🧹 2. 数据清洗 (这里修复了 KeyError)
# ==========================================
def clean_data(df, file_type):
    if df.empty: return df
    
    # 1. 去除列名空格
    df.columns = df.columns.str.strip()
    
    # 2. 映射字典 (包含了所有可能的叫法)
    map_dict = {
        # --- 日期类 ---
        '星期Day': 'Day', '星期': 'Day', '日期': 'Day', 'Day': 'Day', 'Week': 'Day',
        # --- 课程类 ---
        '课程ECA': 'Course', '课程': 'Course', '课程名称': 'Course', 'ECA Activity': 'Course', 'Activity': 'Course', 'Course': 'Course',
        # --- 教师类 ---
        '授课教师 Teacher': 'Teacher', '老师': 'Teacher', '教师': 'Teacher', 'Teacher': 'Teacher', 'Duty Teacher': 'Teacher',
        # --- 教室类 ---
        '教室Class': 'Room', '教室': 'Room', '地点': 'Room', 'Room': 'Room', 'Venue': 'Room',
        # --- 学生姓名类 (你报错的地方) ---
        '学生': 'Student_Name', '姓名': 'Student_Name', '学生姓名': 'Student_Name', 
        'Student Name': 'Student_Name', 'Student_Name': 'Student_Name', 'Student': 'Student_Name',
        'Name': 'Student_Name', 'Full Name': 'Student_Name', '英文名': 'Student_Name', '中文名': 'Student_Name'
    }
    
    df.rename(columns=map_dict, inplace=True)
    
    # 3. 智能模糊搜寻 (如果字典里没有，尝试找包含关键字的列)
    if 'Student_Name' not in df.columns and file_type == 'students':
        for col in df.columns:
            if '名' in col or 'Name' in col or 'Student' in col:
                df.rename(columns={col: 'Student_Name'}, inplace=True)
                break

    # 4. 内容清洗
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
        
    return df

# ==========================================
# 📥 3. 数据加载
# ==========================================
def load_schedule():
    df, err = smart_read(SCHEDULE_FILE)
    if err: st.error(err); return pd.DataFrame()
    return clean_data(df, 'schedule')

def load_students():
    df, err = smart_read(STUDENTS_FILE)
    if err: st.error(err); return pd.DataFrame()
    return clean_data(df, 'students')

def load_logs():
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=["Date", "Time", "Role", "Course", "Teacher", "Room", "Status_Photo", "Absent_Students", "Duty_Rating", "Duty_Comment"]).to_csv(DB_FILE, index=False)
    return pd.read_csv(DB_FILE)

def save_log(entry):
    df = load_logs()
    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
    df.to_csv(DB_FILE, index=False)

# ==========================================
# 📆 4. 获取今日课程
# ==========================================
DAY_MAPPING = {'Monday': '周一', 'Tuesday': '周二', 'Wednesday': '周三', 'Thursday': '周四', 'Friday': '周五', 'Saturday': '周六', 'Sunday': '周日'}

def get_today_courses():
    df = load_schedule()
    if df.empty: return []
    if 'Day' not in df.columns: st.error("⚠️ 课表缺【星期】列"); return []
    
    today_eng = datetime.now().strftime("%A")
    today_chn = DAY_MAPPING.get(today_eng, "未知")
    today_df = df[df['Day'].str.contains(today_eng, case=False, na=False) | df['Day'].str.contains(today_chn, na=False)]
    
    options = []
    if not today_df.empty:
        if 'Teacher' not in today_df.columns: today_df['Teacher'] = "未知"
        for _, row in today_df.iterrows():
            options.append(f"{row['Course']} ({row['Teacher']})")
    return options

# ==========================================
# 🔐 5. 登录系统
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_role' not in st.session_state: st.session_state.user_role = None

def login(role): st.session_state.logged_in = True; st.session_state.user_role = role
def logout(): st.session_state.logged_in = False; st.session_state.user_role = None; st.rerun()

# ==========================================
# 🏠 6. 主程序
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🏫 ECA 智能管理系统</h1>", unsafe_allow_html=True)
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1: 
        if st.button("👨‍🏫 授课老师入口", use_container_width=True): login("teacher"); st.rerun()
    with c2: 
        if st.button("👀 值班巡查入口", use_container_width=True): login("duty"); st.rerun()
    with c3:
        pwd = st.text_input("管理员密码", type="password")
        if pwd == ADMIN_PASSWORD:
            if st.button("📊 进入后台", use_container_width=True): login("admin"); st.rerun()

else:
    with st.sidebar:
        st.header(f"身份: {st.session_state.user_role}")
        st.info(f"📅 {datetime.now().strftime('%A')}")
        if st.button("🚪 退出"): logout()

    # --- 授课老师 ---
    if st.session_state.user_role == "teacher":
        st.header("📸 课前打卡")
        options = get_today_courses()
        
        if not options:
            st.warning("📅 今天没有读取到课程。")
        else:
            # 🟢 1. 先在表单外选择课程 (即时刷新)
            selected_full = st.selectbox("请选择您的课程", options)
            c_name = selected_full.split(" (")[0]
            t_name = selected_full.split("(")[1].strip(")")
            
            # 🟢 2. 计算匹配逻辑
            def normalize(s):
                return str(s).replace('（','').replace('）','').replace('(','').replace(')','').replace(' ','').lower()
            
            df_stu = load_students()
            students = []
            
            # 🚨 防崩溃检查：确认学生表里有名字列
            if not df_stu.empty:
                if 'Student_Name' not in df_stu.columns:
                    # 如果找不到，显示红字提示，并列出所有现有列名
                    st.error("❌ 错误：在学生表里没找到【姓名】列。")
                    st.write("系统读到的所有列名如下，请修改 CSV 表头或联系管理员：")
                    st.code(list(df_stu.columns))
                else:
                    # 正常匹配逻辑
                    if 'Course' in df_stu.columns:
                        target_clean = normalize(c_name)
                        matched_courses = []
                        # 定义敏感词
                        sensitive_keywords = ['校队', 'team', 'schoolteam']

                        for db_course in df_stu['Course'].unique():
                            db_clean = normalize(db_course)
                            if len(db_clean) < 2: continue
                            
                            basic_match = (db_clean in target_clean) or (target_clean in db_clean)
                            if basic_match:
                                target_is_team = any(kw in target_clean for kw in sensitive_keywords)
                                db_is_team = any(kw in db_clean for kw in sensitive_keywords)
                                if target_is_team == db_is_team:
                                    matched_courses.append(db_course)
                        
                        if matched_courses:
                            students = df_stu[df_stu['Course'].isin(matched_courses)]['Student_Name'].tolist()
            
            # 🟢 3. 显示结果与表单
            st.info(f"📍 正在打卡：{c_name}")
            if students:
                st.success(f"✅ 匹配成功！(关联到 {len(students)} 人)")
            else:
                st.warning("⚠️ 未能自动匹配学生名单")
            
            with st.form("checkin"):
                if students:
                    absent = st.multiselect("缺席学生", students)
                else:
                    absent = st.text_input("手动输入缺席名单").split()
                    
                pic = st.camera_input("拍照")
                note = st.text_input("备注")
                
                if st.form_submit_button("🚀 提交"):
                    if not pic: st.error("请拍照")
                    else:
                        save_log({
                            "Date": datetime.now().strftime("%Y-%m-%d"),
                            "Time": datetime.now().strftime("%H:%M:%S"),
                            "Role": "ECA_Teacher",
                            "Course": c_name, "Teacher": t_name, "Room": "详见课表",
                            "Status_Photo": "已上传", 
                            "Absent_Students": ",".join(absent) if absent else "全勤",
                            "Duty_Rating": "", "Duty_Comment": note
                        })
                        st.success("打卡成功！")

    # --- 值班老师 ---
    elif st.session_state.user_role == "duty":
        st.header("👀 实时巡查")
        options = get_today_courses()
        if not options: st.write("今日无课。")
        else:
            target = st.selectbox("巡查课程", options)
            
            df_logs = load_logs()
            today = datetime.now().strftime("%Y-%m-%d")
            c_clean = target.split(" (")[0]
            
            # 检查打卡状态
            is_checked = False
            if not df_logs.empty:
                checked_courses = df_logs[(df_logs['Date']==today) & (df_logs['Role']=='ECA_Teacher')]['Course'].unique()
                if c_clean in checked_courses: is_checked = True
            
            if is_checked: st.success(f"✅ {c_clean} 已打卡")
            else: st.error(f"🚨 {c_clean} 未打卡")
            
            with st.form("duty"):
                rate = st.radio("评价", ["🟢 正常", "🟡 关注", "🔴 严重"], horizontal=True)
                tags = st.multiselect("标签", ["迟到", "玩手机", "早退", "未备课"])
                note = st.text_area("备注")
                if st.form_submit_button("提交反馈"):
                    save_log({
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Time": datetime.now().strftime("%H:%M:%S"),
                        "Role": "Duty_Teacher",
                        "Course": c_clean, "Teacher": target.split("(")[1].strip(")"),
                        "Room": "", "Status_Photo": "", "Absent_Students": "",
                        "Duty_Rating": rate, "Duty_Comment": f"{','.join(tags)} {note}"
                    })
                    st.success("已记录")

    # --- 管理员 ---
    elif st.session_state.user_role == "admin":
        st.header("📊 管理后台")
        tab1, tab2, tab3 = st.tabs(["📋 日志报表", "📅 课表源文件", "🎓 学生名单"])
        with tab1:
            df = load_logs()
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 下载 Excel", df.to_csv(index=False).encode('utf-8-sig'), "report.csv")
        with tab2: st.dataframe(load_schedule(), use_container_width=True)
        with tab3: st.dataframe(load_students(), use_container_width=True)
