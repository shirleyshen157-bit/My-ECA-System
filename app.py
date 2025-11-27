import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ==========================================
# ⚙️ 配置文件名 (保持不变)
# ==========================================
SCHEDULE_FILE = '选课教室及教师安排.csv'
STUDENTS_FILE = '2025-2026 ECA 选课总表.csv'
DB_FILE = 'eca_daily_logs.csv'

st.set_page_config(page_title="ECA 智能追踪系统", layout="wide")

# ==========================================
# 🛠️ 1. 强力读取模块
# ==========================================
def smart_read(filename):
    if not os.path.exists(filename):
        return pd.DataFrame(), f"❌ 找不到文件：{filename}"
    
    # 尝试多种编码
    for enc in ['utf-8-sig', 'gbk', 'utf-16']:
        try:
            # 读取所有列为字符串，防止日期变成了数字
            df = pd.read_csv(filename, encoding=enc, engine='python', on_bad_lines='skip', dtype=str)
            if len(df.columns) < 2: continue
            return df, None
        except:
            continue
    return pd.DataFrame(), f"❌ 无法读取 {filename}，请确保它是标准 CSV 格式。"

# ==========================================
# 🧹 2. 数据清洗 (这里增加了双语识别！)
# ==========================================
def clean_data(df, file_type):
    if df.empty: return df
    
    # 1. 去除列名两边的空格
    df.columns = df.columns.str.strip()
    
    # 2. 映射字典：左边是你要识别的各种写法，右边是系统内部标准名
    map_dict = {
        # --- 针对你截图里的双语表头 ---
        '星期Day': 'Day',
        '课程ECA': 'Course',
        '教室Class': 'Room',
        '授课教师 Teacher': 'Teacher', # 注意中间带空格的情况
        '授课教师Teacher': 'Teacher',
        
        # --- 之前的备用写法 ---
        '星期': 'Day', '日期': 'Day', 'Day': 'Day', 'Week': 'Day',
        '课程': 'Course', '课程名称': 'Course', 'ECA Activity': 'Course',
        '老师': 'Teacher', '教师': 'Teacher', '任课老师': 'Teacher', 'Teacher': 'Teacher',
        '教室': 'Room', '地点': 'Room', 'Room': 'Room',
        '学生': 'Student_Name', '姓名': 'Student_Name', '学生姓名': 'Student_Name', 'Student Name': 'Student_Name'
    }
    
    # 执行重命名
    df.rename(columns=map_dict, inplace=True)
    
    # 3. 把表格里的内容也清理一下空格 (防止 "Thursday " 匹配不上 "Thursday")
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
        pd.DataFrame(columns=[
            "Date", "Time", "Role", "Course", "Teacher", "Room",
            "Status_Photo", "Absent_Students", "Duty_Rating", "Duty_Comment"
        ]).to_csv(DB_FILE, index=False)
    return pd.read_csv(DB_FILE)

def save_log(entry):
    df = load_logs()
    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
    df.to_csv(DB_FILE, index=False)

# ==========================================
# 📆 4. 获取今日课程 (模糊匹配版)
# ==========================================
DAY_MAPPING = {
    'Monday': '周一', 'Tuesday': '周二', 'Wednesday': '周三', 
    'Thursday': '周四', 'Friday': '周五', 'Saturday': '周六', 'Sunday': '周日'
}

def get_today_courses():
    df = load_schedule()
    if df.empty: return []
    
    # 再次检查 Day 列
    if 'Day' not in df.columns:
        st.error("⚠️ 依然找不到日期列。请确认 CSV 表头是否为：[星期Day] 或 [星期] 或 [Day]")
        st.write("目前读到的列名：", list(df.columns))
        return []
    
    # 获取今天 (英文和中文)
    today_eng = datetime.now().strftime("%A") # Thursday
    today_chn = DAY_MAPPING.get(today_eng, "未知") # 周四
    
    # --- 升级逻辑：使用“包含”而不是“等于” ---
    # 只要单元格里包含 "Thursday" 或者 "周四"，就算匹配成功
    # 这样就算你填的是 "周四 Thursday"，也能识别！
    today_df = df[
        df['Day'].str.contains(today_eng, case=False, na=False) | 
        df['Day'].str.contains(today_chn, na=False)
    ]
    
    options = []
    if not today_df.empty:
        if 'Teacher' not in today_df.columns: today_df['Teacher'] = "未知"
        for _, row in today_df.iterrows():
            options.append(f"{row['Course']} ({row['Teacher']})")
            
    return options

# ==========================================
# 🖥️ 5. 界面逻辑
# ==========================================
st.sidebar.title("🚀 ECA 追踪系统")
st.sidebar.info(f"📅 今天是: {datetime.now().strftime('%A')}")

role = st.sidebar.radio("身份选择", ["👨‍🏫 ECA授课老师", "👀 值班老师", "📊 管理后台"])

if role == "👨‍🏫 ECA授课老师":
    st.header("📸 课前打卡")
    options = get_today_courses()
    
    if not options:
        st.warning(f"📅 系统识别今天是 {datetime.now().strftime('%A')}，但课表里没找到课。")
        st.caption("提示：请检查 CSV 里的日期是否包含 'Thursday' 或 '周四'。")
    else:
        with st.form("checkin"):
            sel = st.selectbox("选择课程", options)
            c_name = sel.split(" (")[0]
            teacher_name = sel.split("(")[1].strip(")")
            
            # 找学生
            df_stu = load_students()
            students = []
            if not df_stu.empty and 'Course' in df_stu.columns:
                students = df_stu[df_stu['Course'].str.contains(c_name, regex=False, na=False)]['Student_Name'].tolist()
            
            st.info(f"打卡课程: {c_name}")
            pic = st.camera_input("拍照")
            
            if students:
                absent = st.multiselect("缺席名单", students)
            else:
                st.warning("⚠️ 未关联到学生")
                absent = st.text_input("手动输入").split()
                
            note = st.text_input("备注")
            
            if st.form_submit_button("提交"):
                if not pic: st.error("必须拍照")
                else:
                    save_log({
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Time": datetime.now().strftime("%H:%M:%S"),
                        "Role": "ECA_Teacher",
                        "Course": c_name, "Teacher": teacher_name, "Room": "见课表",
                        "Status_Photo": "已上传", 
                        "Absent_Students": ",".join(absent) if absent else "全勤",
                        "Duty_Rating": "", "Duty_Comment": note
                    })
                    st.success("✅ 打卡成功")

elif role == "👀 值班老师":
    st.header("👀 巡查")
    options = get_today_courses()
    if options:
        df_logs = load_logs()
        today = datetime.now().strftime("%Y-%m-%d")
        done = []
        if not df_logs.empty:
            done = df_logs[(df_logs['Date']==today) & (df_logs['Role']=='ECA_Teacher')]['Course'].unique()
        
        c1, c2 = st.columns(2)
        c1.metric("已打卡", len(done))
        
        missed = [o for o in options if o.split(" (")[0] not in done]
        if missed:
            c2.error("🚨 未打卡")
            for m in missed: c2.write(f"- {m}")
        else:
            c2.success("全部已就位")
            
        st.divider()
        target = st.selectbox("巡查反馈", options)
        with st.form("duty"):
            rate = st.radio("评价", ["🟢 正常", "🟡 问题", "🔴 严重"], horizontal=True)
            tags = st.multiselect("标签", ["迟到", "玩手机", "早退", "未备课"])
            note = st.text_area("备注")
            if st.form_submit_button("提交"):
                save_log({
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Time": datetime.now().strftime("%H:%M:%S"),
                    "Role": "Duty_Teacher",
                    "Course": target.split(" (")[0],
                    "Teacher": target.split("(")[1].strip(")"),
                    "Room": "", "Status_Photo": "", "Absent_Students": "",
                    "Duty_Rating": rate, "Duty_Comment": f"{','.join(tags)} {note}"
                })
                st.success("已记录")
    else:
        st.info("今天无课程。")

elif role == "📊 管理后台":
    st.header("📊 数据与文件")
    st.subheader("打卡记录")
    st.dataframe(load_logs())
    st.subheader("课表读取预览")
    st.dataframe(load_schedule().head())
    st.subheader("学生表读取预览")
    st.dataframe(load_students().head())
