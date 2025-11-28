import streamlit as st
import pandas as pd
from datetime import datetime
import os
import re
import base64

# ==========================================
# ⚙️ 配置区域 / Config
# ==========================================
SCHEDULE_FILE = '选课教室及教师安排.csv'
STUDENTS_FILE = '2025-2026 ECA 选课总表.csv'
DB_FILE = 'eca_daily_logs.csv'
ADMIN_PASSWORD = "8888"
LOGO_FILE = "logo.png"

# 页面配置
st.set_page_config(page_title="CBS ECA System", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 🖼️ 图像处理函数 (实现完美排版的核心)
# ==========================================
def get_img_as_base64(file):
    """将本地图片转换为 Base64 编码，以便在 HTML 中使用"""
    with open(file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# ==========================================
# 🛠️ 智能数据处理核心
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
    if target_name in df.columns: return df
    for col in df.columns:
        for kw in keywords:
            if kw in col:
                df.rename(columns={col: target_name}, inplace=True)
                return df
    return df

def clean_data(df, file_type):
    if df.empty: return df
    df.columns = df.columns.str.strip() 
    map_dict = {
        '星期Day': 'Day', '课程ECA': 'Course', '教室Class': 'Room', 
        '授课教师 Teacher': 'Teacher', '授课教师Teacher': 'Teacher'
    }
    df.rename(columns=map_dict, inplace=True)
    df = auto_find_col(df, ['Day', '星期', '日期', 'Week'], 'Day')
    df = auto_find_col(df, ['Course', '课程', 'Activity', 'ECA'], 'Course')
    df = auto_find_col(df, ['Teacher', '老师', '教师', 'Duty'], 'Teacher')
    df = auto_find_col(df, ['Student', 'Name', '学生', '姓名', '名单'], 'Student_Name')
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
# 🎨 CSS 样式优化
# ==========================================
st.markdown("""
    <style>
    /* 按钮高度优化 */
    .stButton button {
        height: 3.5rem;
        font-weight: bold;
        font-size: 18px;
        border-radius: 10px;
    }
    /* 调整顶部留白 */
    .block-container {
        padding-top: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🏠 首页 / Home
# ==========================================
if not st.session_state.logged_in:
    
    # --- 🟢 完美的头部布局 (Flexbox Layout) ---
    # 如果找到了 Logo 文件，就读取并显示
    header_html = ""
    if os.path.exists(LOGO_FILE):
        img_b64 = get_img_as_base64(LOGO_FILE)
        # 使用 HTML Flexbox 实现：左图右文，垂直居中
        header_html = f"""
        <div style="display: flex; align-items: center; justify-content: flex-start; margin-bottom: 20px;">
            <img src="data:image/png;base64,{img_b64}" style="height: 65px; margin-right: 15px;">
            <div>
                <h1 style="margin: 0; padding: 0; font-size: 26px; line-height: 1.2; color: #1E3A8A; font-weight: 800;">
                    CBS PYP ECA 管理系统
                </h1>
                <p style="margin: 0; padding: 0; font-size: 14px; color: #64748B; font-weight: 500;">
                    Extracurricular Activities Management System
                </p>
            </div>
        </div>
        """
    else:
        # 如果没有 Logo，只显示文字
        header_html = """
        <div style="margin-bottom: 20px;">
            <h1 style="margin: 0; font-size: 26px; color: #1E3A8A;">CBS PYP ECA 管理系统</h1>
            <p style="margin: 0; font-size: 14px; color: #64748B;">Extracurricular Activities Management System</p>
        </div>
        """
    
    st.markdown(header_html, unsafe_allow_html=True)
    
    # --- 登录卡片区 ---
    st.markdown("---") # 分割线
    
    col1, col2, col3 = st.columns([1, 10, 1])
    with col2:
        with st.container(border=True):
            st.markdown("### 👨‍🏫 授课老师 / Teachers")
            if st.button("进入打卡 / Check-in Login", key="btn_t", type="primary", use_container_width=True):
                login("teacher")
                st.rerun()
        
        st.write("") # 空隙

        with st.container(border=True):
            st.markdown("### 👀 值班巡查 / Duty Patrol")
            if st.button("进入巡查 / Patrol Login", key="btn_d", use_container_width=True):
                login("duty")
                st.rerun()
        
        st.write("")
        
        with st.expander("🔐 管理员 / Admin Access"):
            pwd = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Enter Password")
            if st.button("登录后台 / Admin Login", use_container_width=True):
                if pwd == ADMIN_PASSWORD:
                    login("admin")
                    st.rerun()
                else:
                    st.error("Wrong password")

# ==========================================
# 📱 业务界面 (保持不变)
# ==========================================
else:
    with st.sidebar:
        # 侧边栏也显示一个小 Logo
        if os.path.exists(LOGO_FILE):
            st.image(LOGO_FILE, width=60)
        
        st.subheader(f"👤 {st.session_state.user_role.upper()}")
        if st.button("⬅️ 退出 / Logout"): logout()

    # --- 授课老师 ---
    if st.session_state.user_role == "teacher":
        st.markdown("### 📸 课前打卡 / Class Check-in")
        
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
        
        if not options:
            st.warning("📅 No courses found today. (今日无课)")
        else:
            selected_full = st.selectbox("选择课程 / Select Course", options)
            c_name = selected_full.split(" (")[0]
            t_name = selected_full.split("(")[1].strip(")")
            
            df_stu = load_students()
            students = []
            
            if 'Student_Name' not in df_stu.columns:
                st.error("⚠️ System Error: Cannot find student name column.")
            elif 'Course' in df_stu.columns:
                def normalize(s): return str(s).lower().replace(' ','').replace('(','').replace(')','').replace('（','').replace('）','')
                target_clean = normalize(c_name)
                matched_courses = []
                sensitive = ['校队','team']
                
                for db_c in df_stu['Course'].unique():
                    db_clean = normalize(db_c)
                    if len(db_clean)<2: continue
                    if db_clean in target_clean or target_clean in db_clean:
                        t_team = any(k in target_clean for k in sensitive)
                        d_team = any(k in db_clean for k in sensitive)
                        if t_team == d_team:
                            matched_courses.append(db_c)
                
                if matched_courses:
                    students = df_stu[df_stu['Course'].isin(matched_courses)]['Student_Name'].tolist()

            if students:
                st.success(f"✅ Match: {len(students)} Students")
            else:
                st.warning("⚠️ No student list found (未关联到名单)")

            with st.container(border=True):
                with st.form("checkin"):
                    if students:
                        absent = st.multiselect("缺席 / Absent Students", students)
                    else:
                        absent = st.text_input("缺席名单 / Absent Names").split()
                    
                    pic = st.camera_input("拍照 / Photo")
                    note = st.text_input("备注 / Note")
                    
                    if st.form_submit_button("🚀 提交 / Submit", use_container_width=True):
                        if not pic: st.error("Photo required (请拍照)")
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

        if not options: st.info("No courses today (今日无课)")
        else:
            target = st.selectbox("巡查课程 / Target Course", options)
            c_name = target.split(" (")[0]
            
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
                    rate = st.radio("课堂状态 / Class Status", 
                                  ["🟢 正常 / Normal", "🟡 需关注 / Issue", "🔴 严重 / Critical"], 
                                  horizontal=True)
                    tags = st.multiselect("问题标签 / Issue Tags", 
                                          ["Late / 老师迟到", "Playing Phone / 玩手机", 
                                           "No Prep / 未备课", "Early Leave / 早退", 
                                           "Noisy / 纪律差", "Student Safety / 安全隐患"])
                    note = st.text_area("详细备注 / Detailed Note")
                    
                    if st.form_submit_button("提交反馈 / Submit Report", use_container_width=True):
                        save_log({
                            "Date": datetime.now().strftime("%Y-%m-%d"),
                            "Time": datetime.now().strftime("%H:%M:%S"),
                            "Role": "Duty_Teacher", "Course": c_name, "Teacher": target.split("(")[1].strip(")"),
                            "Room": "", "Status_Photo": "", "Absent_Students": "",
                            "Duty_Rating": rate, "Duty_Comment": f"{','.join(tags)} {note}"
                        })
                        st.success("Recorded (已记录)")

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
