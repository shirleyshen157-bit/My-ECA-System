import streamlit as st
import pandas as pd
from datetime import datetime
import os
import re

# ==========================================
# ⚙️ 配置区域 / Config
# ==========================================
SCHEDULE_FILE = '选课教室及教师安排.csv'
STUDENTS_FILE = '2025-2026 ECA 选课总表.csv'
DB_FILE = 'eca_daily_logs.csv'
ADMIN_PASSWORD = "8888"

st.set_page_config(page_title="ECA System", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 🛠️ 智能数据处理核心 (修复报错的关键)
# ==========================================
def smart_read(filename):
    if not os.path.exists(filename): return pd.DataFrame(), f"❌ File not found: {filename}"
    for enc in ['utf-8-sig', 'gbk', 'utf-16']:
        try:
            df = pd.read_csv(filename, encoding=enc, engine='python', on_bad_lines='skip', dtype=str)
            if len(df.columns) < 2: continue
            return df, None
        except: continue
    return pd.DataFrame(), f"❌ Cannot read: {filename}"

def auto_find_col(df, keywords, target_name):
    """猎犬算法：在列名中嗅探关键字"""
    # 如果已经存在目标列，直接返回
    if target_name in df.columns: return df
    
    # 遍历所有列名
    for col in df.columns:
        # 只要列名包含关键字之一
        for kw in keywords:
            if kw in col:
                df.rename(columns={col: target_name}, inplace=True)
                return df
    return df

def clean_data(df, file_type):
    if df.empty: return df
    df.columns = df.columns.str.strip() # 去空格
    
    # 1. 暴力字典映射 (处理特殊双语表头)
    map_dict = {
        '星期Day': 'Day', '课程ECA': 'Course', '教室Class': 'Room', 
        '授课教师 Teacher': 'Teacher', '授课教师Teacher': 'Teacher'
    }
    df.rename(columns=map_dict, inplace=True)
    
    # 2. 猎犬搜索 (模糊匹配，解决 KeyError)
    # 找日期列
    df = auto_find_col(df, ['Day', '星期', '日期', 'Week'], 'Day')
    # 找课程列
    df = auto_find_col(df, ['Course', '课程', 'Activity', 'ECA'], 'Course')
    # 找老师列
    df = auto_find_col(df, ['Teacher', '老师', '教师', 'Duty'], 'Teacher')
    # 找学生列 (你报错的地方)
    df = auto_find_col(df, ['Student', 'Name', '学生', '姓名', '名单'], 'Student_Name')
    
    # 3. 内容清洗
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

# ==========================================
# 🔐 登录逻辑
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
# 🎨 CSS 样式优化 (解决字体过大问题)
# ==========================================
st.markdown("""
    <style>
    /* 缩小手机端标题字号 */
    .custom-title {
        font-size: 1.8rem !important; 
        font-weight: 700;
        color: #0F172A;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .custom-subtitle {
        font-size: 1rem !important;
        color: #64748B;
        text-align: center;
        margin-bottom: 2rem;
    }
    /* 优化卡片间距 */
    .stButton button {
        height: 3rem;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🏠 首页 / Home
# ==========================================
if not st.session_state.logged_in:
    # 优化的标题区
    st.markdown('<div class="custom-title">ECA 智能管理系统</div>', unsafe_allow_html=True)
    st.markdown('<div class="custom-subtitle">ECA Management System</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 10, 1])
    with col2:
        # 授课老师入口
        with st.container(border=True):
            st.markdown("**👨‍🏫 授课老师 / Teachers**")
            if st.button("进入打卡 / Login", key="btn_t", type="primary", use_container_width=True):
                login("teacher")
                st.rerun()
        
        st.write("") # 增加空隙

        # 值班老师入口
        with st.container(border=True):
            st.markdown("**👀 值班巡查 / Duty Patrol**")
            if st.button("进入巡查 / Login", key="btn_d", use_container_width=True):
                login("duty")
                st.rerun()
        
        st.write("")
        
        # 管理员
        with st.expander("🔐 管理员 / Admin"):
            pwd = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Password")
            if st.button("Go", use_container_width=True):
                if pwd == ADMIN_PASSWORD:
                    login("admin")
                    st.rerun()
                else:
                    st.error("Wrong password")

# ==========================================
# 📱 业务界面
# ==========================================
else:
    # 顶部导航栏
    with st.sidebar:
        st.header(f"👤 {st.session_state.user_role.upper()}")
        if st.button("⬅️ 退出 / Logout"): logout()

    # --- 授课老师 ---
    if st.session_state.user_role == "teacher":
        st.markdown("### 📸 课前打卡 / Check-in")
        
        # 获取课程逻辑
        df_sch = load_schedule()
        today_eng = datetime.now().strftime("%A")
        today_chn = {'Monday':'周一','Tuesday':'周二','Wednesday':'周三','Thursday':'周四','Friday':'周五'}.get(today_eng,'')
        
        options = []
        if not df_sch.empty and 'Day' in df_sch.columns:
            # 模糊匹配日期
            mask = df_sch['Day'].str.contains(today_eng, case=False, na=False) | df_sch['Day'].str.contains(today_chn, na=False)
            df_today = df_sch[mask]
            for _, row in df_today.iterrows():
                t = row.get('Teacher', 'Unknown')
                options.append(f"{row['Course']} ({t})")
        
        if not options:
            st.warning("📅 No courses found today. (今日无课)")
        else:
            # 下拉框放在表单外，实现即时刷新
            selected_full = st.selectbox("选择课程 / Select Course", options)
            c_name = selected_full.split(" (")[0]
            t_name = selected_full.split("(")[1].strip(")")
            
            # --- 匹配学生 ---
            df_stu = load_students()
            students = []
            
            # 这里的检查至关重要：如果没找到列，显示优雅的提示
            if 'Student_Name' not in df_stu.columns:
                st.error("⚠️ System Error: Cannot find student name column.")
                st.caption(f"Columns detected: {list(df_stu.columns)}")
            elif 'Course' in df_stu.columns:
                # 匹配逻辑
                def normalize(s): return str(s).lower().replace(' ','').replace('(','').replace(')','').replace('（','').replace('）','')
                target_clean = normalize(c_name)
                matched_courses = []
                sensitive = ['校队','team']
                
                for db_c in df_stu['Course'].unique():
                    db_clean = normalize(db_c)
                    if len(db_clean)<2: continue
                    if db_clean in target_clean or target_clean in db_clean:
                        # 校队隔离逻辑
                        t_team = any(k in target_clean for k in sensitive)
                        d_team = any(k in db_clean for k in sensitive)
                        if t_team == d_team:
                            matched_courses.append(db_c)
                
                if matched_courses:
                    students = df_stu[df_stu['Course'].isin(matched_courses)]['Student_Name'].tolist()

            # 显示状态
            if students:
                st.success(f"✅ Match: {len(students)} Students")
            else:
                st.warning("⚠️ No student list found (未关联到名单)")

            # 表单
            with st.container(border=True):
                with st.form("checkin"):
                    if students:
                        absent = st.multiselect("缺席 / Absent", students)
                    else:
                        absent = st.text_input("缺席名单 / Absent Names").split()
                    
                    pic = st.camera_input("拍照 / Photo")
                    note = st.text_input("备注 / Note")
                    
                    if st.form_submit_button("🚀 提交 / Submit", use_container_width=True):
                        if not pic: st.error("Photo required")
                        else:
                            save_log({
                                "Date": datetime.now().strftime("%Y-%m-%d"),
                                "Time": datetime.now().strftime("%H:%M:%S"),
                                "Role": "ECA_Teacher", "Course": c_name, "Teacher": t_name, "Room": "",
                                "Status_Photo": "Uploaded", "Absent_Students": ",".join(absent) if absent else "All Present",
                                "Duty_Rating": "", "Duty_Comment": note
                            })
                            st.success("Success!")

    # --- 值班老师 ---
    elif st.session_state.user_role == "duty":
        st.markdown("### 👀 实时巡查 / Duty Patrol")
        
        # (重复上面的获取课程逻辑)
        df_sch = load_schedule()
        today_eng = datetime.now().strftime("%A")
        today_chn = {'Monday':'周一','Tuesday':'周二','Wednesday':'周三','Thursday':'周四','Friday':'周五'}.get(today_eng,'')
        options = []
        if not df_sch.empty and 'Day' in df_sch.columns:
            mask = df_sch['Day'].str.contains(today_eng, case=False, na=False) | df_sch['Day'].str.contains(today_chn, na=False)
            df_today = df_sch[mask]
            for _, row in df_today.iterrows():
                t = row.get('Teacher', 'Unknown')
                options.append(f"{row['Course']} ({t})")

        if not options: st.info("No courses today.")
        else:
            target = st.selectbox("巡查课程 / Target Course", options)
            c_name = target.split(" (")[0]
            
            # 检查状态
            logs = load_logs()
            today_str = datetime.now().strftime("%Y-%m-%d")
            checked = False
            if not logs.empty:
                checked_courses = logs[(logs['Date']==today_str) & (logs['Role']=='ECA_Teacher')]['Course'].unique()
                if c_name in checked_courses: checked = True
            
            if checked: st.success(f"✅ Checked-in (已打卡)")
            else: st.error(f"🚨 Not Checked-in (未打卡)")
            
            with st.container(border=True):
                with st.form("duty"):
                    rate = st.radio("Status", ["🟢 Normal", "🟡 Issue", "🔴 Critical"], horizontal=True)
                    tags = st.multiselect("Tags", ["Late/迟到", "Phone/玩手机", "No Prep/无备课", "Leave Early/早退"])
                    note = st.text_area("Note / 备注")
                    if st.form_submit_button("Submit / 提交", use_container_width=True):
                        save_log({
                            "Date": datetime.now().strftime("%Y-%m-%d"),
                            "Time": datetime.now().strftime("%H:%M:%S"),
                            "Role": "Duty_Teacher", "Course": c_name, "Teacher": target.split("(")[1].strip(")"),
                            "Room": "", "Status_Photo": "", "Absent_Students": "",
                            "Duty_Rating": rate, "Duty_Comment": f"{','.join(tags)} {note}"
                        })
                        st.success("Recorded")

    # --- 管理员 ---
    elif st.session_state.user_role == "admin":
        st.header("📊 Admin Dashboard")
        tab1, tab2, tab3 = st.tabs(["Logs", "Schedule", "Students"])
        with tab1:
            df = load_logs()
            st.dataframe(df, use_container_width=True)
            st.download_button("Download CSV", df.to_csv(index=False).encode('utf-8-sig'), "report.csv")
        with tab2: st.dataframe(load_schedule(), use_container_width=True)
        with tab3: st.dataframe(load_students(), use_container_width=True)
