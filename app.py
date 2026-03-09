import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import base64

# ==========================================
# ⚙️ 配置区域 / Config
# ==========================================
SCHEDULE_FILE = '选课教室及教师安排.csv'
STUDENTS_FILE = '2025-2026 ECA 选课总表.csv'
DB_FILE = 'eca_daily_logs.csv'
ADMIN_PASSWORD = "8888"
LOGO_FILE = "logo.png"

st.set_page_config(page_title="CBS ECA System", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 🖼️ 图像与工具函数
# ==========================================
def get_img_as_base64(file):
    with open(file, "rb") as f: data = f.read()
    return base64.b64encode(data).decode()

def smart_read(filename):
    if not os.path.exists(filename): return pd.DataFrame(), f"❌ File not found: {filename}"
    for enc in ['utf-8-sig', 'gbk', 'utf-16']:
        try:
            df = pd.read_csv(filename, encoding=enc, engine='python', on_bad_lines='skip', dtype=str)
            if len(df.columns) < 2: continue
            return df, None
        except: continue
    return pd.DataFrame(), f"❌ Cannot read: {filename}"

def auto_find_col(df, keywords):
    for col in df.columns:
        for kw in keywords:
            if kw in col: return col
    return None

# ==========================================
# 🧹 智能数据清洗 
# ==========================================
def clean_data(df, file_type):
    if df.empty: return df
    df.columns = df.columns.str.strip()
    
    rename_map = {
        '星期Day': 'Day', '课程ECA': 'Course', '教室Class': 'Room', 
        '授课教师 Teacher': 'Teacher', '授课教师Teacher': 'Teacher'
    }
    df.rename(columns=rename_map, inplace=True)
    
    col_day = auto_find_col(df,['Day', '星期', '日期', 'Week'])
    col_course = auto_find_col(df,['Course', '课程', 'Activity', 'ECA'])
    col_teacher = auto_find_col(df,['Teacher', '老师', '教师', 'Duty'])
    
    if col_day: df.rename(columns={col_day: 'Day'}, inplace=True)
    if col_course: df.rename(columns={col_course: 'Course'}, inplace=True)
    if col_teacher: df.rename(columns={col_teacher: 'Teacher'}, inplace=True)

    if file_type == 'students':
        col_cn = auto_find_col(df, ['中文', '姓名', 'Student', 'Name', '学生'])
        col_en = auto_find_col(df,['English', '英文', 'En_Name'])
        if col_en and col_cn and col_en != col_cn:
            df['Student_Name'] = df[col_cn].astype(str) + " (" + df[col_en].astype(str) + ")"
        elif col_cn:
            df.rename(columns={col_cn: 'Student_Name'}, inplace=True)
            
        col_class = auto_find_col(df,['班级', 'Class', '班', 'Grade', '年级'])
        if col_class: 
            df.rename(columns={col_class: 'Class'}, inplace=True)
        else:
            df['Class'] = "未分配"
        
    for col in df.columns: df[col] = df[col].astype(str).str.strip()
    return df

def load_schedule():
    df, err = smart_read(SCHEDULE_FILE)
    if err: return pd.DataFrame()
    return clean_data(df, 'schedule')

def load_students():
    df, err = smart_read(STUDENTS_FILE)
    if err: return pd.DataFrame()
    return clean_data(df, 'students')

# ==========================================
# 💾 数据保存模块
# ==========================================
def save_students(df):
    if 'Course' in df.columns and 'Student_Name' in df.columns and 'Class' in df.columns:
        df = df[['Course', 'Class', 'Student_Name']]
        df.to_csv(STUDENTS_FILE, index=False, encoding='utf-8-sig')

def load_logs():
    columns =["Date", "Time", "Role", "Course", "Teacher", "Room", 
               "Status_Photo", "Absent_Students", "Duty_Rating", "Duty_Comment",
               "Lesson_Topic", "WeChat_Feedback"]
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=columns).to_csv(DB_FILE, index=False)
    return pd.read_csv(DB_FILE)

def save_log(entry):
    df = load_logs()
    for key in entry:
        if key not in df.columns: df[key] = ""
    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
    df.to_csv(DB_FILE, index=False)

# ==========================================
# 🔐 登录 & 基础逻辑
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_role' not in st.session_state: st.session_state.user_role = None

def login(role): st.session_state.logged_in = True; st.session_state.user_role = role
def logout(): st.session_state.logged_in = False; st.session_state.user_role = None; st.rerun()

st.markdown("""
    <style>
    .block-container { padding-top: 3rem !important; padding-bottom: 2rem !important; }
    .main-title { font-size: 28px !important; font-weight: 900; color: #1E3A8A; line-height: 1.2; margin: 0; }
    .sub-title { font-size: 14px !important; color: #64748B; font-weight: 500; margin: 0; }
    .section-header { font-size: 20px !important; font-weight: 700; color: #334155; margin-bottom: 5px; }
    .stButton button { height: 3.5rem; font-size: 16px; font-weight: 600; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

DAY_MAPPING = {'Monday': '周一', 'Tuesday': '周二', 'Wednesday': '周三', 'Thursday': '周四', 'Friday': '周五', 'Saturday': '周六', 'Sunday': '周日'}

def get_today_courses():
    df = load_schedule()
    if df.empty or 'Day' not in df.columns: return[]
    today_eng = datetime.now().strftime("%A")
    today_chn = DAY_MAPPING.get(today_eng, "未知")
    today_df = df[df['Day'].str.contains(today_eng, case=False, na=False) | df['Day'].str.contains(today_chn, na=False)]
    options =[]
    if not today_df.empty:
        if 'Teacher' not in today_df.columns: today_df['Teacher'] = "Unknown"
        for _, row in today_df.iterrows(): options.append(f"{row['Course']} ({row['Teacher']})")
    return options

# ==========================================
# 🏠 首页
# ==========================================
if not st.session_state.logged_in:
    header_html = ""
    if os.path.exists(LOGO_FILE):
        img_b64 = get_img_as_base64(LOGO_FILE)
        header_html = f"""
        <div style="display: flex; align-items: center; margin-bottom: 25px;">
            <img src="data:image/png;base64,{img_b64}" style="height: 70px; margin-right: 15px;">
            <div><div class="main-title">CBS PYP ECA 管理系统</div><div class="sub-title">Extracurricular Activities Management System</div></div>
        </div>
        """
    else:
        header_html = """<div style="margin-bottom: 25px;"><div class="main-title">CBS PYP ECA 管理系统</div><div class="sub-title">Extracurricular Activities Management System</div></div>"""
    
    st.markdown(header_html, unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 10, 1])
    with col2:
        with st.container(border=True):
            st.markdown('<div class="section-header">👨‍🏫 授课老师 / Teachers</div>', unsafe_allow_html=True)
            if st.button("进入打卡 / Check-in Login", key="btn_t", type="primary", use_container_width=True): login("teacher"); st.rerun()
        st.write("") 
        with st.container(border=True):
            st.markdown('<div class="section-header">👀 值班巡查 / Duty Patrol</div>', unsafe_allow_html=True)
            if st.button("进入巡查 / Patrol Login", key="btn_d", use_container_width=True): login("duty"); st.rerun()
        st.write("")
        with st.expander("🔐 管理员 / Admin Access"):
            pwd = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Enter Password")
            if st.button("登录 / Login", use_container_width=True):
                if pwd == ADMIN_PASSWORD: login("admin"); st.rerun()
                else: st.error("Wrong password")

# ==========================================
# 📱 业务界面
# ==========================================
else:
    with st.sidebar:
        if os.path.exists(LOGO_FILE): st.image(LOGO_FILE, width=60)
        st.write(f"**{st.session_state.user_role.upper()}**")
        st.write(f"📅 {datetime.now().strftime('%Y-%m-%d')}")
        if st.button("⬅️ 退出 / Logout"): logout()

    # --- 👨‍🏫 授课老师 ---
    if st.session_state.user_role == "teacher":
        st.markdown("### 📸 课前打卡 / Class Check-in")
        options = get_today_courses()
        
        if not options:
            st.warning("📅 今日无课 / No courses today.")
        else:
            selected_full = st.selectbox("选择课程 / Select Course", options)
            c_name = selected_full.split(" (")[0]
            t_name = selected_full.split("(")[1].strip(")")
            
            df_stu = load_students()
            students_display =[] 
            
            if not df_stu.empty and 'Course' in df_stu.columns and 'Student_Name' in df_stu.columns:
                def normalize(s): return str(s).lower().replace(' ','').replace('(','').replace(')','').replace('（','').replace('）','')
                target_clean = normalize(c_name)
                matched_courses = []
                sensitive =['校队','team']
                
                for db_c in df_stu['Course'].unique():
                    db_clean = normalize(db_c)
                    if len(db_clean)<2: continue
                    if db_clean in target_clean or target_clean in db_clean:
                        t_team = any(k in target_clean for k in sensitive)
                        d_team = any(k in db_clean for k in sensitive)
                        if t_team == d_team: matched_courses.append(db_c)
                        
                if matched_courses:
                    matched_df = df_stu[df_stu['Course'].isin(matched_courses)]
                    if 'Class' in matched_df.columns:
                        students_display = (matched_df['Class'] + " ｜ " + matched_df['Student_Name']).tolist()
                    else:
                        students_display = matched_df['Student_Name'].tolist()

            if students_display: st.success(f"✅ Match: {len(students_display)} Students")
            else: st.warning("⚠️ No student list found")

            with st.container(border=True):
                with st.form("checkin"):
                    st.markdown("#### 1. 教学主题 / Lesson Topic")
                    lesson_topic = st.text_input("本节课内容 / Enter topic", placeholder="例如: 正手击球")
                    
                    st.markdown("#### 2. 考勤 / Attendance")
                    if students_display: 
                        absent = st.multiselect("缺席 / Absent", students_display)
                    else: 
                        absent = st.text_input("缺席名单 / Absent Names").split()
                    
                    st.markdown("#### 3. 反馈确认 / WeChat Feedback")
                    wechat_done = st.checkbox("✅ 本周已在企微群发布反馈? / Posted feedback in WeChat?")
                    
                    st.markdown("#### 4. 拍照 (教案或板书) / Photo")
                    pic = st.camera_input("拍照 / Take Photo")
                    
                    if st.form_submit_button("🚀 提交 / Submit", use_container_width=True):
                        if not pic: st.error("Photo required")
                        elif not lesson_topic: st.error("Lesson Topic required")
                        else:
                            save_log({
                                "Date": datetime.now().strftime("%Y-%m-%d"), "Time": datetime.now().strftime("%H:%M:%S"),
                                "Role": "ECA_Teacher", "Course": c_name, "Teacher": t_name, "Room": "",
                                "Status_Photo": "Uploaded", "Absent_Students": ",".join(absent) if absent else "All Present",
                                "Duty_Rating": "", "Duty_Comment": "", "Lesson_Topic": lesson_topic, "WeChat_Feedback": "Yes" if wechat_done else "No"
                            })
                            st.success("Success!")

    # --- 👀 值班老师 ---
    elif st.session_state.user_role == "duty":
        st.markdown("### 👀 实时巡查 / Duty Patrol")
        options = get_today_courses()

        if not options: st.info("No courses today")
        else:
            target = st.selectbox("巡查课程 / Target Course", options)
            c_name = target.split(" (")[0]
            
            logs = load_logs()
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            teacher_log = pd.DataFrame()
            if not logs.empty:
                teacher_log = logs[(logs['Date']==today_str) & (logs['Role']=='ECA_Teacher') & (logs['Course']==c_name)]
            
            if not teacher_log.empty:
                topic = teacher_log.iloc[-1]['Lesson_Topic']
                st.success(f"✅ 已打卡 (Checked-in) | 主题: {topic}")
            else:
                st.error(f"🚨 未打卡 / Not Checked-in")
            
            with st.container(border=True):
                with st.form("duty"):
                    rate = st.radio("状态 / Status",["🟢 Normal", "🟡 Issue", "🔴 Critical"], horizontal=True)
                    tags = st.multiselect("标签 / Tags",["Late/迟到", "Phone/玩手机", "No Prep/无备课", "Early Leave/早退", "Safety/安全隐患", "Off Topic/随意上课"])
                    note = st.text_area("备注 / Note")
                    if st.form_submit_button("提交 / Submit", use_container_width=True):
                        save_log({
                            "Date": datetime.now().strftime("%Y-%m-%d"), "Time": datetime.now().strftime("%H:%M:%S"),
                            "Role": "Duty_Teacher", "Course": c_name, "Teacher": target.split("(")[1].strip(")"),
                            "Room": "", "Status_Photo": "", "Absent_Students": "", "Duty_Rating": rate, "Duty_Comment": f"{','.join(tags)} {note}",
                            "Lesson_Topic": "", "WeChat_Feedback": ""
                        })
                        st.success("Recorded")

    # --- 📊 管理员 ---
    elif st.session_state.user_role == "admin":
        st.header("📊 Admin Dashboard")
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 周报统计", "🛠️ 名单动态管理", "📋 完整日志", "📅 课表", "🎓 当前名单"])
        
        with tab1:
            st.markdown("### 📢 企微反馈监控 (WeChat Feedback Monitor)")
            df = load_logs()
            if not df.empty:
                df_t = df[df['Role'] == 'ECA_Teacher'].copy()
                if not df_t.empty:
                    stats = df_t.groupby('Course').agg(
                        CheckIn_Count=('Date', 'count'),
                        Feedback_Count=('WeChat_Feedback', lambda x: (x == 'Yes').sum()),
                        Last_Topic=('Lesson_Topic', 'last'),
                        Teacher=('Teacher', 'last')
                    ).reset_index()
                    def highlight_row(row):
                        if row['CheckIn_Count'] >= 2 and row['Feedback_Count'] == 0: return['background-color: #ffe4e6'] * len(row)
                        return [''] * len(row)
                    st.dataframe(stats.style.apply(highlight_row, axis=1), use_container_width=True)
                else: st.info("No data")
            else: st.info("No data")

        # ========================================================
        # 🔥 全新升级：级联菜单式 (班级 -> 学生 -> 原ECA -> 新ECA) 
        # ========================================================
        with tab2:
            st.markdown("### 🛠️ 教务中心：学生变更 (Student Management)")
            st.info("💡 **操作提示**：左侧选班级，右侧选学生，下方执行操作。完成所有调整后，请务必在页面最底部下载最新名单覆盖到 GitHub。")
            
            df_stu = load_students()
            df_sch = load_schedule()
            
            all_courses =[]
            if not df_sch.empty and 'Course' in df_sch.columns:
                all_courses = sorted(df_sch['Course'].unique().tolist())
            
            if df_stu.empty or 'Course' not in df_stu.columns or 'Student_Name' not in df_stu.columns:
                st.error("数据未准备好。请检查原始文件。")
            else:
                if 'Class' not in df_stu.columns: df_stu['Class'] = "未分配"
                # 提取所有存在的班级
                all_classes = sorted(df_stu['Class'].unique().tolist())
                
                col_m1, col_m2, col_m3 = st.columns(3)
                
                # ----------------- 功能 1: 增加新生 -----------------
                with col_m1:
                    with st.container(border=True):
                        st.markdown("#### ➕ 增加新生 (Add)")
                        # 提供下拉选择现有班级，或者输入新班级的选项
                        is_new_class = st.checkbox("🆕 该生在全新的班级?")
                        if is_new_class:
                            new_class = st.text_input("输入新班级名", placeholder="例如: G1-A")
                        else:
                            new_class = st.selectbox("选择所属班级", all_classes, key="add_cls")
                            
                        new_name = st.text_input("输入学生姓名 (中英文)")
                        new_course = st.selectbox("分配 ECA 课程", all_courses, key="add_course")
                        
                        if st.button("确认添加 / Add", type="primary", use_container_width=True):
                            if new_name and new_class:
                                new_row = pd.DataFrame([{'Course': new_course, 'Class': new_class, 'Student_Name': new_name}])
                                df_stu = pd.concat([df_stu, new_row], ignore_index=True)
                                save_students(df_stu)
                                st.success(f"已将 {new_name} 加入 {new_course}！")
                                st.rerun()
                            else:
                                st.error("姓名和班级不能为空")

                # ----------------- 功能 2: 调换课程 -----------------
                with col_m2:
                    with st.container(border=True):
                        st.markdown("#### 🔄 调换课程 (Transfer)")
                        
                        # 步骤 1：先选班级
                        trans_class = st.selectbox("1. 选择班级", all_classes, key="t_class")
                        
                        # 步骤 2：过滤该班级下的学生
                        trans_students = sorted(df_stu[df_stu['Class'] == trans_class]['Student_Name'].unique().tolist())
                        if not trans_students:
                            st.warning("该班级目前没有学生数据")
                        else:
                            trans_stu = st.selectbox("2. 选择学生", trans_students, key="t_stu")
                            
                            # 步骤 3：查找该学生当前正在上的 ECA 课程
                            current_ecas = df_stu[(df_stu['Class'] == trans_class) & (df_stu['Student_Name'] == trans_stu)]['Course'].tolist()
                            
                            if not current_ecas:
                                st.warning("该学生目前未分配任何ECA课程")
                            else:
                                trans_old_course = st.selectbox("3. 当前ECA (将被换掉)", current_ecas, key="t_old")
                                # 步骤 4：选择新课程
                                trans_new_course = st.selectbox("4. 选择新ECA课程",[c for c in all_courses if c != trans_old_course], key="t_new")
                                
                                if st.button("确认调换 / Transfer", use_container_width=True):
                                    # 精准定位要修改的那一行
                                    mask = (df_stu['Class'] == trans_class) & (df_stu['Student_Name'] == trans_stu) & (df_stu['Course'] == trans_old_course)
                                    df_stu.loc[mask, 'Course'] = trans_new_course
                                    save_students(df_stu)
                                    st.success(f"已将 {trans_stu} 转入 {trans_new_course}！")
                                    st.rerun()

                # ----------------- 功能 3: 移除学生 -----------------
                with col_m3:
                    with st.container(border=True):
                        st.markdown("#### ❌ 移除学生 (Remove)")
                        
                        # 步骤 1：先选班级
                        del_class = st.selectbox("1. 选择班级", all_classes, key="d_class")
                        
                        # 步骤 2：过滤学生
                        del_students = sorted(df_stu[df_stu['Class'] == del_class]['Student_Name'].unique().tolist())
                        if not del_students:
                            st.warning("该班级目前没有学生数据")
                        else:
                            del_stu = st.selectbox("2. 选择学生", del_students, key="d_stu")
                            
                            # 步骤 3：查找该学生当前的 ECA 课程
                            del_ecas = df_stu[(df_stu['Class'] == del_class) & (df_stu['Student_Name'] == del_stu)]['Course'].tolist()
                            
                            if not del_ecas:
                                st.warning("该学生目前未分配任何ECA课程")
                            else:
                                del_old_course = st.selectbox("3. 确认要移除的ECA", del_ecas, key="d_old")
                                
                                if st.button("确认移除 / Remove", use_container_width=True):
                                    # 精准定位并反向过滤（删除该行）
                                    mask = (df_stu['Class'] == del_class) & (df_stu['Student_Name'] == del_stu) & (df_stu['Course'] == del_old_course)
                                    df_stu = df_stu[~mask]
                                    save_students(df_stu)
                                    st.success(f"已将 {del_stu} 从 {del_old_course} 中移除！")
                                    st.rerun()
            
            # --- 终极保存下载区 ---
            st.markdown("---")
            st.markdown("### 📥 第 2 步：下载最新名单并归档")
            st.warning("⚠️ **非常重要：** 云端系统重启会导致以上修改流失。请务必点击下方按钮，下载最新的 `2025-2026 ECA 选课总表.csv`，然后去 GitHub 上覆盖原文件，实现永久保存！")
            
            df_latest = load_students()
            # 下载时保证格式统一，且包含班级
            csv_data = df_latest.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 下载最新排课大名单 (CSV)",
                data=csv_data,
                file_name='2025-2026 ECA 选课总表.csv',
                mime='text/csv',
                type="primary"
            )

        with tab3:
            df = load_logs()
            st.dataframe(df, use_container_width=True)
            st.download_button("Download Logs", df.to_csv(index=False).encode('utf-8-sig'), "logs.csv")
        with tab4: st.dataframe(load_schedule(), use_container_width=True)
        with tab5: st.dataframe(load_students(), use_container_width=True)
