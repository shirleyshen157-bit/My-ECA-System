import streamlit as st
import pandas as pd
from datetime import datetime
import os
import re

# ==========================================
# ⚙️ 配置区域 / Configuration
# ==========================================
SCHEDULE_FILE = '选课教室及教师安排.csv'
STUDENTS_FILE = '2025-2026 ECA 选课总表.csv'
DB_FILE = 'eca_daily_logs.csv'
ADMIN_PASSWORD = "8888"

# 页面设置：使用宽屏模式，并折叠侧边栏以保持首页简洁
st.set_page_config(page_title="ECA 智能管理系统", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 🛠️ 核心功能函数 / Core Functions
# ==========================================
def smart_read(filename):
    if not os.path.exists(filename): return pd.DataFrame(), f"❌ 找不到文件 / File not found: {filename}"
    for enc in ['utf-8-sig', 'gbk', 'utf-16']:
        try:
            df = pd.read_csv(filename, encoding=enc, engine='python', on_bad_lines='skip', dtype=str)
            if len(df.columns) < 2: continue
            return df, None
        except: continue
    return pd.DataFrame(), f"❌ 无法读取 / Cannot read: {filename}"

def clean_data(df, file_type):
    if df.empty: return df
    df.columns = df.columns.str.strip()
    map_dict = {
        '星期Day': 'Day', '星期': 'Day', '日期': 'Day', 'Day': 'Day',
        '课程ECA': 'Course', '课程': 'Course', '课程名称': 'Course', 'ECA Activity': 'Course',
        '教室Class': 'Room', '教室': 'Room', '地点': 'Room', 'Room': 'Room',
        '授课教师 Teacher': 'Teacher', '授课教师Teacher': 'Teacher', '老师': 'Teacher', '教师': 'Teacher', 'Teacher': 'Teacher',
        '学生': 'Student_Name', '姓名': 'Student_Name', '学生姓名': 'Student_Name', 'Student Name': 'Student_Name'
    }
    df.rename(columns=map_dict, inplace=True)
    for col in df.columns: df[col] = df[col].astype(str).str.strip()
    return df

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

DAY_MAPPING = {'Monday': '周一', 'Tuesday': '周二', 'Wednesday': '周三', 'Thursday': '周四', 'Friday': '周五', 'Saturday': '周六', 'Sunday': '周日'}

def get_today_courses():
    df = load_schedule()
    if df.empty: return []
    if 'Day' not in df.columns: st.error("⚠️ 课表缺【星期】列 / Missing 'Day' column"); return []
    
    today_eng = datetime.now().strftime("%A")
    today_chn = DAY_MAPPING.get(today_eng, "未知")
    today_df = df[df['Day'].str.contains(today_eng, case=False, na=False) | df['Day'].str.contains(today_chn, na=False)]
    
    options = []
    if not today_df.empty:
        if 'Teacher' not in today_df.columns: today_df['Teacher'] = "Unknown"
        for _, row in today_df.iterrows():
            options.append(f"{row['Course']} ({row['Teacher']})")
    return options

# ==========================================
# 🔐 登录管理 / Login Manager
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_role' not in st.session_state: st.session_state.user_role = None

def login(role):
    st.session_state.logged_in = True
    st.session_state.user_role = role

def logout():
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.rerun()

# ==========================================
# 🏠 首页：登录门户 / Login Portal
# ==========================================
if not st.session_state.logged_in:
    # 顶部留白
    st.write("") 
    st.write("") 
    
    # 标题区域
    st.markdown(
        """
        <h1 style='text-align: center; color: #1E3A8A;'>🏫 ECA 智能管理系统</h1>
        <h3 style='text-align: center; color: #64748B;'>ECA Management System</h3>
        <hr style='margin-top: 2rem; margin-bottom: 2rem;'>
        """, 
        unsafe_allow_html=True
    )
    
    # 登录卡片布局
    col_spacer_1, col_main, col_spacer_2 = st.columns([1, 6, 1]) # 限制宽度，手机端更好看
    
    with col_main:
        # 授课老师卡片
        with st.container(border=True):
            st.markdown("### 👨‍🏫 授课老师 / Teachers")
            st.caption("课前打卡 & 考勤 / Check-in & Attendance")
            if st.button("进入系统 / Login", key="btn_teacher", type="primary", use_container_width=True):
                login("teacher")
                st.rerun()
        
        st.write("") # 增加间距

        # 值班巡查卡片
        with st.container(border=True):
            st.markdown("### 👀 值班巡查 / Duty Patrol")
            st.caption("实时监控 & 反馈 / Monitoring & Feedback")
            if st.button("进入系统 / Login", key="btn_duty", use_container_width=True):
                login("duty")
                st.rerun()
        
        st.write("")

        # 管理员区域 (折叠起来，保持界面干净)
        with st.expander("🔐 管理员入口 / Admin Access"):
            pwd = st.text_input("密码 / Password", type="password")
            if st.button("登录后台 / Admin Login", use_container_width=True):
                if pwd == ADMIN_PASSWORD:
                    login("admin")
                    st.rerun()
                else:
                    st.error("密码错误 / Wrong Password")

# ==========================================
# 📱 业务页面 / Business Pages
# ==========================================
else:
    # 侧边栏
    with st.sidebar:
        st.title(f"👤 {st.session_state.user_role.upper()}")
        st.info(f"📅 {datetime.now().strftime('%Y-%m-%d %A')}")
        if st.button("🚪 退出登录 / Logout"): logout()

    # --- 角色 1: 授课老师 (Teacher) ---
    if st.session_state.user_role == "teacher":
        st.header("📸 课前打卡 / Class Check-in")
        st.markdown("---")
        
        options = get_today_courses()
        
        if not options:
            st.warning("📅 今天没有读取到您的课程安排。\n\nNo courses found for today.")
        else:
            # 1. 选择课程
            selected_full = st.selectbox("请选择您的课程 / Select Your Course", options)
            c_name = selected_full.split(" (")[0]
            t_name = selected_full.split("(")[1].strip(")")
            
            # 2. 匹配逻辑
            def normalize(s):
                return str(s).replace('（','').replace('）','').replace('(','').replace(')','').replace(' ','').lower()
            
            df_stu = load_students()
            students = []
            
            if not df_stu.empty and 'Course' in df_stu.columns:
                target_clean = normalize(c_name)
                matched_courses = []
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
            
            # 3. 状态显示
            with st.container(border=True):
                st.info(f"📍 正在打卡 / Checking in: **{c_name}**")
                if students:
                    st.success(f"✅ 匹配成功! (关联 {len(students)} 人)\n\nMatch Success! ({len(students)} students)")
                else:
                    st.warning("⚠️ 未关联到学生 / No students linked")

                with st.form("checkin"):
                    st.markdown("#### 1. 考勤 / Attendance")
                    if students:
                        absent = st.multiselect("缺席学生 (默认为全勤) / Select Absent Students", students)
                    else:
                        absent = st.text_input("手动输入缺席名单 / Enter Absent Names").split()
                    
                    st.markdown("#### 2. 拍照 / Photo Proof")
                    pic = st.camera_input("拍摄教室环境 / Take Classroom Photo")
                    
                    st.markdown("#### 3. 备注 / Note")
                    note = st.text_input("可选 / Optional")
                    
                    if st.form_submit_button("🚀 提交 / Submit", use_container_width=True):
                        if not pic: st.error("❌ 必须拍照 / Photo is required")
                        else:
                            save_log({
                                "Date": datetime.now().strftime("%Y-%m-%d"),
                                "Time": datetime.now().strftime("%H:%M:%S"),
                                "Role": "ECA_Teacher",
                                "Course": c_name, "Teacher": t_name, "Room": "See Schedule",
                                "Status_Photo": "Uploaded", 
                                "Absent_Students": ",".join(absent) if absent else "All Present",
                                "Duty_Rating": "", "Duty_Comment": note
                            })
                            st.balloons()
                            st.success("✅ 打卡成功 / Check-in Successful!")

    # --- 角色 2: 值班老师 (Duty) ---
    elif st.session_state.user_role == "duty":
        st.header("👀 实时巡查 / Duty Patrol")
        st.markdown("---")
        
        options = get_today_courses()
        if not options: st.write("今日无课 / No courses today.")
        else:
            target = st.selectbox("选择巡查课程 / Select Course", options)
            c_clean = target.split(" (")[0]
            
            # 状态卡片
            df_logs = load_logs()
            today = datetime.now().strftime("%Y-%m-%d")
            is_checked = False
            if not df_logs.empty:
                checked_courses = df_logs[(df_logs['Date']==today) & (df_logs['Role']=='ECA_Teacher')]['Course'].unique()
                if c_clean in checked_courses: is_checked = True
            
            if is_checked: 
                st.success(f"✅ 该课程已课前打卡 / Teacher has checked in.")
            else: 
                st.error(f"🚨 该课程尚未打卡！/ Teacher has NOT checked in!")
            
            with st.container(border=True):
                st.markdown("#### 📝 巡查反馈 / Patrol Report")
                with st.form("duty"):
                    rate = st.radio("评价 / Status", ["🟢 正常 / Normal", "🟡 关注 / Issue", "🔴 严重 / Critical"], horizontal=True)
                    tags = st.multiselect("问题标签 / Issue Tags", 
                                          ["迟到 / Late", "玩手机 / Phone Use", "早退 / Leave Early", "未备课 / No Prep", "纪律差 / Noisy"])
                    note = st.text_area("详细备注 / Details")
                    
                    if st.form_submit_button("提交反馈 / Submit Report", use_container_width=True):
                        save_log({
                            "Date": datetime.now().strftime("%Y-%m-%d"),
                            "Time": datetime.now().strftime("%H:%M:%S"),
                            "Role": "Duty_Teacher",
                            "Course": c_clean, "Teacher": target.split("(")[1].strip(")"),
                            "Room": "", "Status_Photo": "", "Absent_Students": "",
                            "Duty_Rating": rate, "Duty_Comment": f"{','.join(tags)} {note}"
                        })
                        st.success("✅ 已记录 / Recorded")

    # --- 角色 3: 管理员 (Admin) ---
    elif st.session_state.user_role == "admin":
        st.header("📊 管理后台 / Admin Dashboard")
        
        tab1, tab2, tab3 = st.tabs(["📋 日志 / Logs", "📅 课表 / Schedule", "🎓 名单 / Students"])
        
        with tab1:
            st.caption("所有打卡与巡查记录 / All check-in & patrol records")
            df = load_logs()
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 下载 Excel / Download", df.to_csv(index=False).encode('utf-8-sig'), "report.csv")
            
        with tab2: 
            st.dataframe(load_schedule(), use_container_width=True)
        with tab3: 
            st.dataframe(load_students(), use_container_width=True)
