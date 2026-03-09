import streamlit as st
import pandas as pd
from datetime import datetime
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

# 💎 强制规定的行政班级列表 (Homerooms)
HOMEROOMS =['G1A', 'G1B', 'G1C', 'G2A', 'G2B', 'G2C', 'G3A', 'G3B', 'G3C', 'G4A', 'G4B', 'G5A', 'G5B']

st.set_page_config(page_title="CBS ECA System", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 🖼️ 图像与工具函数
# ==========================================
def get_img_as_base64(file):
    with open(file, "rb") as f: data = f.read()
    return base64.b64encode(data).decode()

def smart_read(filename):
    if not os.path.exists(filename): return pd.DataFrame(), f"❌ File not found: {filename}"
    for enc in['utf-8-sig', 'gbk', 'utf-16']:
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
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.columns = df.columns.str.strip()
    
    if file_type == 'schedule':
        rename_map = {'星期Day': 'Day', '课程ECA': 'Course', '教室Class': 'Room', '授课教师 Teacher': 'Teacher', '授课教师Teacher': 'Teacher'}
        df.rename(columns=rename_map, inplace=True)
        if 'Day' not in df.columns:
            c = auto_find_col(df, ['Day', '星期', '日期'])
            if c: df.rename(columns={c: 'Day'}, inplace=True)
        if 'Course' not in df.columns:
            c = auto_find_col(df, ['Course', '课程', 'ECA'])
            if c: df.rename(columns={c: 'Course'}, inplace=True)
        if 'Teacher' not in df.columns:
            c = auto_find_col(df,['Teacher', '老师', '教师'])
            if c: df.rename(columns={c: 'Teacher'}, inplace=True)

    elif file_type == 'students':
        rename_map = {
            '课程ECA': 'Course', '课程': 'Course',
            '班级Class': 'Class', '行政班': 'Class', '班级': 'Class',
            '学生姓名Student': 'Student_Name_CN', '中文名': 'Student_Name_CN', '姓名': 'Student_Name_CN',
            '学生英文名': 'Student_Name_EN', '英文名': 'Student_Name_EN',
            '性别Gender': 'Gender', '性别': 'Gender'
        }
        df.rename(columns=rename_map, inplace=True)
        
        if 'Course' not in df.columns:
            c = auto_find_col(df,['Course', '课程'])
            if c: df.rename(columns={c: 'Course'}, inplace=True)
        if 'Class' not in df.columns:
            c = auto_find_col(df,['Class', '班级'])
            if c: df.rename(columns={c: 'Class'}, inplace=True)
        if 'Student_Name_CN' not in df.columns:
            c = auto_find_col(df,['Student', '姓名', '中文'])
            if c: df.rename(columns={c: 'Student_Name_CN'}, inplace=True)
        if 'Student_Name_EN' not in df.columns:
            c = auto_find_col(df, ['English', '英文'])
            if c: df.rename(columns={c: 'Student_Name_EN'}, inplace=True)
        if 'Gender' not in df.columns:
            c = auto_find_col(df,['Gender', '性别'])
            if c: df.rename(columns={c: 'Gender'}, inplace=True)

        if 'Class' not in df.columns: df['Class'] = "未分配"
        if 'Course' not in df.columns: df['Course'] = "未分配"
        if 'Student_Name_CN' not in df.columns: df['Student_Name_CN'] = "未知"
        if 'Student_Name_EN' not in df.columns: df['Student_Name_EN'] = ""
        if 'Gender' not in df.columns: df['Gender'] = ""
        
        df = df.fillna('').replace({'nan': '', 'None': '', 'NaN': ''})
        df['Student_Name'] = df.apply(
            lambda x: f"{x['Student_Name_CN']} ({x['Student_Name_EN']})" if str(x['Student_Name_EN']).strip() else str(x['Student_Name_CN']), 
            axis=1
        )
    
    df = df.loc[:, ~df.columns.duplicated()]
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
# 📊 智能排课分类器
# ==========================================
def get_course_categories(df_sch):
    categories = {}
    if df_sch.empty or 'Course' not in df_sch.columns or 'Day' not in df_sch.columns: return categories
    
    for course, group in df_sch.groupby('Course'):
        days_str = " ".join(group['Day'].astype(str).str.lower().tolist())
        mon = 'mon' in days_str or '一' in days_str
        tue = 'tue' in days_str or '二' in days_str
        wed = 'wed' in days_str or '三' in days_str
        thu = 'thu' in days_str or '四' in days_str
        fri = 'fri' in days_str or '五' in days_str
        
        if tue and thu and fri: cat = "📌 周二、四、五 (校队)"
        elif mon and wed: cat = "📌 周一、三 (ECA)"
        elif tue and thu: cat = "📌 周二、四 (ECA)"
        elif fri: cat = "📌 周五 (思维校队)"
        else: cat = "📌 其他时段"
        categories[course] = cat
    return categories

# ==========================================
# 💾 数据保存模块 (强力排序版)
# ==========================================
def save_students(df):
    export_df = pd.DataFrame()
    export_df['学生姓名Student'] = df.get('Student_Name_CN', '')
    export_df['学生英文名'] = df.get('Student_Name_EN', '')
    export_df['性别Gender'] = df.get('Gender', '')
    export_df['班级Class'] = df.get('Class', '')
    export_df['课程ECA'] = df.get('Course', '')
    
    export_df = export_df.sort_values(by=['课程ECA', '班级Class'])
    export_df.to_csv(STUDENTS_FILE, index=False, encoding='utf-8-sig')

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
# 🔐 登录 & UI
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
                        students_display = ("【" + matched_df['Class'] + "】 " + matched_df['Student_Name']).tolist()
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
                        absent = st.multiselect("缺席 / Absent", sorted(students_display))
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
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎓 分班名单总览", "🛠️ 名单动态管理", "📊 周报统计", "📋 完整日志", "📅 排课表"])
        
        # ========================================================
        # 🎓 模块 1: 分类查看最新课程名单
        # ========================================================
        with tab1:
            st.markdown("### 🎓 各班级最新名单检索 (Sorted Rosters)")
            df_latest_stu = load_students()
            df_latest_sch = load_schedule()
            
            if not df_latest_stu.empty:
                cat_map = get_course_categories(df_latest_sch)
                df_latest_stu['Category'] = df_latest_stu['Course'].map(lambda x: cat_map.get(x, "📌 其他时段"))
                all_cats = sorted(df_latest_stu['Category'].unique().tolist())
                
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    selected_cat = st.selectbox("1. 选择排课类型 / Schedule Type",["所有类型 (All)"] + all_cats)
                
                if selected_cat != "所有类型 (All)":
                    filtered_by_cat = df_latest_stu[df_latest_stu['Category'] == selected_cat]
                else:
                    filtered_by_cat = df_latest_stu
                    
                available_courses = sorted(filtered_by_cat['Course'].unique().tolist())
                
                with col_f2:
                    selected_course = st.selectbox("2. 选择具体课程 / Course", ["所有课程 (All)"] + available_courses)
                
                if selected_course != "所有课程 (All)":
                    display_df = filtered_by_cat[filtered_by_cat['Course'] == selected_course]
                    st.success(f"**{selected_course}** 当前共有 **{len(display_df)}** 名学生。")
                else:
                    display_df = filtered_by_cat
                    st.info(f"当前筛选条件共计: **{len(display_df)}** 名学生。")
                
                display_df = display_df.sort_values(by=['Course', 'Class'])
                st.dataframe(display_df[['Course', 'Class', 'Student_Name_CN', 'Student_Name_EN', 'Gender']].reset_index(drop=True), use_container_width=True)
            else:
                st.error("数据为空")

        # ========================================================
        # 🛠️ 模块 2: 教务中心 (2x2 矩阵式布局)
        # ========================================================
        with tab2:
            st.markdown("### 🛠️ 教务中心：学生增删改查 (Student Management)")
            st.info("💡 请按行政班级依次检索。修改完成后，务必至页面底部下载最新名单归档！")
            
            df_stu = load_students()
            df_sch = load_schedule()
            all_courses = sorted(df_sch['Course'].unique().tolist()) if not df_sch.empty else[]
            
            if df_stu.empty:
                st.error("⚠️ 数据未准备好。")
            else:
                # 分成两行两列
                row1_col1, row1_col2 = st.columns(2)
                row2_col1, row2_col2 = st.columns(2)
                
                # --- 功能 1: 库内学生加课 (满足你的核心需求) ---
                with row1_col1:
                    with st.container(border=True):
                        st.markdown("#### 👤 为已有学生加课 (Enroll Existing)")
                        st.caption("适用于：系统里已有该生信息，需要给TA报一门新ECA。系统自动读取TA的中英文名。")
                        
                        e_class = st.selectbox("1. 找行政班级", HOMEROOMS, key="e_cls")
                        class_df = df_stu[df_stu['Class'] == e_class]
                        unique_students_df = class_df[['Student_Name_CN', 'Student_Name_EN', 'Gender', 'Student_Name']].drop_duplicates()
                        
                        if unique_students_df.empty:
                            st.warning("该班级目前无任何学生数据")
                        else:
                            e_stu_display = st.selectbox("2. 选学生", unique_students_df['Student_Name'].tolist(), key="e_stu")
                            e_course = st.selectbox("3. 分配新ECA", all_courses, key="e_course")
                            
                            if st.button("确认加课 / Enroll", type="primary", use_container_width=True):
                                exists = df_stu[(df_stu['Class'] == e_class) & (df_stu['Student_Name'] == e_stu_display) & (df_stu['Course'] == e_course)]
                                if not exists.empty:
                                    st.error("该生已经在这门课里了！")
                                else:
                                    stu_info = unique_students_df[unique_students_df['Student_Name'] == e_stu_display].iloc[0]
                                    new_row = pd.DataFrame([{
                                        'Course': e_course, 'Class': e_class,
                                        'Student_Name_CN': stu_info['Student_Name_CN'],
                                        'Student_Name_EN': stu_info['Student_Name_EN'],
                                        'Gender': stu_info['Gender'],
                                        'Student_Name': stu_info['Student_Name']
                                    }])
                                    df_stu = pd.concat([df_stu, new_row], ignore_index=True)
                                    save_students(df_stu)
                                    st.success(f"已为 {e_stu_display} 成功增加 {e_course}！")
                                    st.rerun()

                # --- 功能 2: 录入全新学生 ---
                with row1_col2:
                    with st.container(border=True):
                        st.markdown("#### 🆕 录入全新学生 (Add Brand New)")
                        st.caption("适用于：转校生或从未在系统里出现过的新生。")
                        add_class = st.selectbox("1. 选择行政班级", HOMEROOMS, key="n_cls")
                        new_cn = st.text_input("2. 中文姓名 (必填)", placeholder="例如：黄钰棋")
                        new_en = st.text_input("3. 英文名 (选填)", placeholder="例如：Frank")
                        new_gender = st.selectbox("4. 性别",["男", "女", ""])
                        new_course = st.selectbox("5. 分配首个 ECA", all_courses, key="n_course")
                        
                        if st.button("确认录入 / Add New", type="primary", use_container_width=True):
                            if new_cn:
                                new_row = pd.DataFrame([{
                                    'Course': new_course, 'Class': add_class, 
                                    'Student_Name_CN': new_cn, 'Student_Name_EN': new_en, 'Gender': new_gender,
                                    'Student_Name': f"{new_cn} ({new_en})" if new_en else new_cn
                                }])
                                df_stu = pd.concat([df_stu, new_row], ignore_index=True)
                                save_students(df_stu)
                                st.success("录入成功！")
                                st.rerun()
                            else:
                                st.error("中文姓名不能为空！")

                # --- 功能 3: 调换ECA ---
                with row2_col1:
                    with st.container(border=True):
                        st.markdown("#### 🔄 调换ECA (Transfer)")
                        trans_class = st.selectbox("1. 找行政班级", HOMEROOMS, key="t_class")
                        students_in_class = sorted(df_stu[df_stu['Class'] == trans_class]['Student_Name'].unique().tolist())
                        
                        if not students_in_class: st.warning("无数据")
                        else:
                            trans_stu = st.selectbox("2. 选学生", students_in_class, key="t_stu")
                            current_ecas = df_stu[(df_stu['Class'] == trans_class) & (df_stu['Student_Name'] == trans_stu)]['Course'].tolist()
                            
                            if not current_ecas: st.warning("该生未分配ECA")
                            else:
                                trans_old_course = st.selectbox("3. 该生原ECA (将被退掉)", current_ecas, key="t_old")
                                trans_new_course = st.selectbox("4. 换成新ECA",[c for c in all_courses if c != trans_old_course], key="t_new")
                                
                                if st.button("确认调换 / Transfer", use_container_width=True):
                                    mask = (df_stu['Class'] == trans_class) & (df_stu['Student_Name'] == trans_stu) & (df_stu['Course'] == trans_old_course)
                                    df_stu.loc[mask, 'Course'] = trans_new_course
                                    save_students(df_stu)
                                    st.success("调换成功！")
                                    st.rerun()

                # --- 功能 4: 移除学生 ---
                with row2_col2:
                    with st.container(border=True):
                        st.markdown("#### ❌ 从ECA退课 (Drop Course)")
                        del_class = st.selectbox("1. 找行政班级", HOMEROOMS, key="d_class")
                        del_students_in_class = sorted(df_stu[df_stu['Class'] == del_class]['Student_Name'].unique().tolist())
                        
                        if not del_students_in_class: st.warning("无数据")
                        else:
                            del_stu = st.selectbox("2. 选学生", del_students_in_class, key="d_stu")
                            del_ecas = df_stu[(df_stu['Class'] == del_class) & (df_stu['Student_Name'] == del_stu)]['Course'].tolist()
                            
                            if not del_ecas: st.warning("该生未分配ECA")
                            else:
                                del_old_course = st.selectbox("3. 要退出的ECA", del_ecas, key="d_old")
                                if st.button("确认退课 / Drop", use_container_width=True):
                                    mask = (df_stu['Class'] == del_class) & (df_stu['Student_Name'] == del_stu) & (df_stu['Course'] == del_old_course)
                                    df_stu = df_stu[~mask]
                                    save_students(df_stu)
                                    st.success("退课成功！")
                                    st.rerun()
            
            # --- 下载区 ---
            st.markdown("---")
            st.markdown("### 📥 最终步骤：下载最新总表并归档至 GitHub")
            
            df_latest = load_students()
            export_df = pd.DataFrame()
            export_df['学生姓名Student'] = df_latest.get('Student_Name_CN', '')
            export_df['学生英文名'] = df_latest.get('Student_Name_EN', '')
            export_df['性别Gender'] = df_latest.get('Gender', '')
            export_df['班级Class'] = df_latest.get('Class', '')
            export_df['课程ECA'] = df_latest.get('Course', '')
            # 自动强力排序
            export_df = export_df.sort_values(by=['课程ECA', '班级Class'])
            
            csv_data = export_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 下载已完美排序的 2025-2026 ECA 选课总表.csv",
                data=csv_data,
                file_name='2025-2026 ECA 选课总表.csv',
                mime='text/csv',
                type="primary"
            )

        # 其他页面
        with tab3:
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

        with tab4:
            df = load_logs()
            st.dataframe(df, use_container_width=True)
            st.download_button("Download Logs", df.to_csv(index=False).encode('utf-8-sig'), "logs.csv")
        with tab5: 
            st.dataframe(load_schedule(), use_container_width=True)
