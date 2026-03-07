import streamlit as st
import google.generativeai as genai
from docx import Document
from pptx import Presentation
import re, os, random, io, time
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import hashlib

# -------------------------
# Load environment variables
# -------------------------
load_dotenv()
try:
    gemini_key = os.environ.get("GEMINI_API_KEY") or st.secrets["GEMINI_API_KEY"]
except:
    gemini_key = None

# -------------------------
# Constants & Folders
# -------------------------
TEMPLATE_DIR = "templates"
PREVIEW_DIR = "template_previews"
DOWNLOAD_LOG = "downloads.csv"
USERS_DB = "teachers.csv"
SAVED_RESOURCES_DB = "saved_resources.csv"

os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(PREVIEW_DIR, exist_ok=True)

available_templates = [f for f in os.listdir(TEMPLATE_DIR) if f.endswith(".pptx")]

# -------------------------
# Helper Functions
# -------------------------
def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)

def create_card_preview(text, color="#4B8BBE"):
    img = Image.new("RGB", (400,250), color)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except:
        font = ImageFont.load_default()
    text = text.replace("_"," ").title()
    bbox = draw.textbbox((0,0), text, font=font)
    w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text(((400-w)/2,(250-h)/2), text, fill="white", font=font)
    return img

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_teacher(username, password, email):
    df = pd.read_csv(USERS_DB) if os.path.exists(USERS_DB) else pd.DataFrame(columns=["username","password_hash","email","role"])
    if username in df['username'].values:
        return False, "Username already exists"
    new = pd.DataFrame([[username, hash_password(password), email, "teacher"]], columns=df.columns)
    df = pd.concat([df,new], ignore_index=True)
    df.to_csv(USERS_DB, index=False)
    return True, "Registered successfully"

def login_teacher(username, password):
    if not os.path.exists(USERS_DB):
        return False, "No users yet"
    df = pd.read_csv(USERS_DB)
    user = df[df['username']==username]
    if user.empty:
        return False, "Username not found"
    if hash_password(password) != user['password_hash'].values[0]:
        return False, "Incorrect password"
    return True, user.iloc[0].to_dict()

def save_resource_for_teacher(username, resource_name, r_type, path, is_public=False):
    df = pd.read_csv(SAVED_RESOURCES_DB) if os.path.exists(SAVED_RESOURCES_DB) else pd.DataFrame(
        columns=["teacher_username","resource_name","type","path","timestamp","is_public","likes"])
    df = pd.concat([df,pd.DataFrame([[username,resource_name,r_type,path,datetime.now(),is_public,0]], columns=df.columns)], ignore_index=True)
    df.to_csv(SAVED_RESOURCES_DB, index=False)

def log_download(resource_name, user="anonymous"):
    row = pd.DataFrame([[resource_name, user, datetime.now()]], columns=["Resource","User","Timestamp"])
    if os.path.exists(DOWNLOAD_LOG):
        row.to_csv(DOWNLOAD_LOG, mode="a", header=False, index=False)
    else:
        row.to_csv(DOWNLOAD_LOG, index=False)

def generate_lesson(prompt, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    return response.text

# -------------------------
# Session State Init
# -------------------------
if "requests_today" not in st.session_state:
    st.session_state.requests_today = 0
if "last_request" not in st.session_state:
    st.session_state.last_request = 0
if "logged_in_teacher" not in st.session_state:
    st.session_state.logged_in_teacher = None
if "login_prompt" not in st.session_state:
    st.session_state.login_prompt = False
if "chosen_template" not in st.session_state:
    st.session_state.chosen_template = None

# -------------------------
# Streamlit Page Setup
# -------------------------
st.set_page_config(page_title="AI Teacher Resource Finder", page_icon="🎓", layout="wide")

# -------------------------
# Sidebar Navigation
# -------------------------
st.sidebar.title("Navigation")
menu = st.sidebar.radio("Menu", ["Home", "Download Analytics", "Settings"])

# -------------------------
# Hero Section
# -------------------------
st.markdown("""
<div style="
background: linear-gradient(135deg,#4B8BBE,#306998);
padding:30px;
border-radius:15px;
color:white;
text-align:center;
margin-bottom:20px;">
<h1>🎓 AI Teacher Resource Finder</h1>
<p style="font-size:18px;">Create lesson plans and PowerPoint slides instantly using AI</p>
</div>
""", unsafe_allow_html=True)

# -------------------------
# HOME PAGE
# -------------------------
if menu == "Home":
    st.subheader("🔍 Search Templates / Community Resources")
    search_query = st.text_input("Search template/resource", "")
    filtered_templates = [t for t in available_templates if search_query.lower() in t.lower()] if search_query else available_templates

    # ---------------- Guest / Teacher Marketplace Preview ----------------
    st.subheader("🎨 Browse Templates / Community Resources")
    cols = st.columns(3)

    # Load community resources
    community_df = pd.read_csv(SAVED_RESOURCES_DB) if os.path.exists(SAVED_RESOURCES_DB) else pd.DataFrame(
        columns=["teacher_username","resource_name","type","path","timestamp","is_public","likes"])
    if search_query:
        community_df = community_df[community_df["resource_name"].str.lower().str.contains(search_query.lower())]

    resources_to_show = filtered_templates + community_df["resource_name"].tolist() + ["🎲 Random Template"]

    for i, resource in enumerate(resources_to_show):
        col = cols[i % 3]
        with col:
            preview_path = os.path.join(PREVIEW_DIR, f"{resource}.png")
            if os.path.exists(preview_path):
                st.image(preview_path, use_container_width=True)
            else:
                img = create_card_preview(resource)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                st.image(buf.getvalue(), use_container_width=True)
            st.markdown(f"**{resource}**")
            
            # Guest / Teacher Actions
            if st.session_state.get("logged_in_teacher"):
                if st.button(f"Select {resource}", key=f"btn_{i}"):
                    st.session_state["chosen_template"] = resource
                    st.success(f"Selected {resource}")
            else:
                if st.button(f"Request Download", key=f"guest_{i}"):
                    st.session_state.login_prompt = True

    # ---------------- Login Prompt for Guests ----------------
    if st.session_state.login_prompt:
        st.warning("You must log in or register to download or generate lessons.")
        st.session_state.login_prompt = False

    # ---------------- Public Community Section ----------------
    st.subheader("🌍 Public Community Resources")
    public_df = community_df[community_df["is_public"]==True] if not community_df.empty else pd.DataFrame(columns=community_df.columns)
    if not public_df.empty:
        cols = st.columns(3)
        for i, row in public_df.iterrows():
            col = cols[i % 3]
            with col:
                preview_path = os.path.join(PREVIEW_DIR, f"{row['resource_name']}.png")
                if os.path.exists(preview_path):
                    st.image(preview_path, use_container_width=True)
                else:
                    img = create_card_preview(row['resource_name'])
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    st.image(buf.getvalue(), use_container_width=True)
                
                st.markdown(f"**{row['resource_name']}** by {row['teacher_username']}")
                st.markdown(f"👍 {row['likes']} likes")
                if st.session_state.get("logged_in_teacher"):
                    if st.button(f"Like {row['resource_name']}", key=f"like_{i}"):
                        df = pd.read_csv(SAVED_RESOURCES_DB)
                        idx = df[df["resource_name"]==row['resource_name']].index[0]
                        df.at[idx,'likes'] += 1
                        df.to_csv(SAVED_RESOURCES_DB, index=False)
                        st.experimental_rerun()

    # ---------------- Teacher-only Section ----------------
    if st.session_state.get("logged_in_teacher"):
        chosen_template = st.session_state.get("chosen_template", None)
        topic = st.text_input("📘 Lesson Topic")

        # ---------------- Teacher Analytics ----------------
        teacher = st.session_state["logged_in_teacher"]
        st.markdown("### 📊 Your Analytics")
        df_saved = pd.read_csv(SAVED_RESOURCES_DB) if os.path.exists(SAVED_RESOURCES_DB) else pd.DataFrame(
            columns=["teacher_username","resource_name","type","path","timestamp","is_public","likes"])
        df_downloads = pd.read_csv(DOWNLOAD_LOG) if os.path.exists(DOWNLOAD_LOG) else pd.DataFrame(columns=["Resource","User","Timestamp"])
        user_saved = df_saved[df_saved["teacher_username"] == teacher["username"]]
        downloads_user = df_downloads.merge(user_saved, left_on="Resource", right_on="resource_name", how="inner")
        total_generated = len(user_saved)
        total_downloads = len(downloads_user)
        most_used_template = user_saved['resource_name'].value_counts().idxmax() if not user_saved.empty else "N/A"
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Lessons Generated", total_generated)
        col2.metric("Total Downloads of Your Resources", total_downloads)
        col3.metric("Most Used Template", most_used_template)
        st.markdown("#### 📈 Downloads per Template")
        if not downloads_user.empty:
            chart_data = downloads_user['resource_name'].value_counts()
            st.bar_chart(chart_data)
        else:
            st.info("No downloads yet.")

        # ---------------- Generate Lesson ----------------
        if st.button("✨ Generate Lesson"):
            current_time = time.time()
            if current_time - st.session_state.last_request < 10:
                st.warning("Please wait 10 seconds before generating another lesson.")
                st.stop()
            st.session_state.last_request = current_time
            if st.session_state.requests_today >= 5:
                st.warning("⚠️ Daily generation limit reached (5 lessons per session).")
                st.stop()

            if not topic:
                st.warning("Enter lesson topic")
                st.stop()
            if not chosen_template:
                st.warning("Select a template first")
                st.stop()
            if not gemini_key:
                st.error("Gemini API key missing")
                st.stop()

            with st.spinner("Generating lesson..."):
                prompt = f"""
Create a structured lesson plan for {topic}.
Include:
1. Objectives
2. Introduction
3. Key Teaching Points
4. Activities
5. Assessment
6. Summary
7. Slide Outline
"""
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        lesson_text = generate_lesson(prompt, gemini_key)
                        break
                    except Exception as e:
                        if "ResourceExhausted" in str(e) and attempt < max_retries - 1:
                            time.sleep(5)
                        elif "Quota exceeded" in str(e) or "429" in str(e):
                            st.error("Gemini API quota exceeded. Try again later.")
                            st.stop()
                        else:
                            st.error(f"Error: {e}")
                            st.stop()

                safe_topic = sanitize_filename(topic)
                word_file = f"{safe_topic}_lesson.docx"
                ppt_file = f"{safe_topic}_slides.pptx"

                # Save Word
                doc = Document()
                doc.add_heading(f"Lesson Plan: {topic}", level=1)
                doc.add_paragraph(lesson_text)
                doc.save(word_file)

                # Save PPT
                template_to_use = chosen_template if chosen_template != "🎲 Random Template" else random.choice(available_templates)
                prs = Presentation(os.path.join(TEMPLATE_DIR, template_to_use))
                sections = [s.strip() for s in lesson_text.split("\n\n") if s.strip()]
                for section in sections:
                    slide = prs.slides.add_slide(prs.slide_layouts[1])
                    lines = section.split("\n")
                    slide.shapes.title.text = lines[0]
                    if len(lines) > 1:
                        slide.placeholders[1].text = "\n".join(lines[1:])
                prs.save(ppt_file)

                teacher_username = st.session_state["logged_in_teacher"]["username"]
                is_public = st.checkbox("🌐 Share this lesson publicly?", value=False)
                col1, col2 = st.columns(2)
                with col1:
                    with open(word_file,"rb") as f:
                        if st.download_button("📄 Download Word", f, file_name=word_file):
                            log_download(word_file, teacher_username)
                            save_resource_for_teacher(teacher_username, word_file, "Word", os.path.abspath(word_file), is_public)
                with col2:
                    with open(ppt_file,"rb") as f:
                        if st.download_button("🎞️ Download Slides", f, file_name=ppt_file):
                            log_download(ppt_file, teacher_username)
                            save_resource_for_teacher(teacher_username, ppt_file, "PPT", os.path.abspath(ppt_file), is_public)

# -------------------------
# Download Analytics Page
# -------------------------
if menu=="Download Analytics":
    st.subheader("📊 Resource Downloads")
    if os.path.exists(DOWNLOAD_LOG):
        df = pd.read_csv(DOWNLOAD_LOG)
        st.dataframe(df)
        st.bar_chart(df["Resource"].value_counts())
    else:
        st.info("No downloads yet")

# -------------------------
# Settings Page (Login/Register + Profile)
# -------------------------
st.subheader("Teacher Login / Register / Profile")
tab1, tab2, tab3 = st.tabs(["Login","Register","Profile"])

# ---- Login ----
with tab1:
    username = st.text_input("Username","",key="login_user")
    password = st.text_input("Password","",type="password",key="login_pass")
    if st.button("Login"):
        ok, res = login_teacher(username,password)
        if ok:
            st.success("Logged in successfully")
            st.session_state["logged_in_teacher"] = res
        else:
            st.error(res)

# ---- Register ----
with tab2:
    r_username = st.text_input("Username","",key="reg_user")
    r_email = st.text_input("Email","",key="reg_email")
    r_password = st.text_input("Password","",type="password",key="reg_pass")
    if st.button("Register"):
        ok, msg = register_teacher(r_username,r_password,r_email)
        if ok:
            st.success(msg)
        else:
            st.error(msg)

# ---- Profile ----
with tab3:
    if st.session_state.get("logged_in_teacher"):
        teacher = st.session_state["logged_in_teacher"]
        st.markdown(f"**Username:** {teacher['username']}")
        st.markdown(f"**Email:** {teacher['email']}")

        # Change password
        st.markdown("### 🔑 Change Password")
        current_pass = st.text_input("Current Password", type="password", key="current_pass")
        new_pass = st.text_input("New Password", type="password", key="new_pass")
        confirm_pass = st.text_input("Confirm New Password", type="password", key="confirm_pass")
        if st.button("Update Password"):
            df_users = pd.read_csv(USERS_DB)
            user_idx = df_users[df_users["username"]==teacher["username"]].index[0]
            if hash_password(current_pass) != df_users.at[user_idx, "password_hash"]:
                st.error("Current password is incorrect")
            elif new_pass != confirm_pass:
                st.error("New passwords do not match")
            else:
                df_users.at[user_idx,"password_hash"] = hash_password(new_pass)
                df_users.to_csv(USERS_DB, index=False)
                st.success("Password updated successfully")

        # Manage saved resources
        st.markdown("### 💾 Your Saved Resources")
        df_saved = pd.read_csv(SAVED_RESOURCES_DB) if os.path.exists(SAVED_RESOURCES_DB) else pd.DataFrame(
            columns=["teacher_username","resource_name","type","path","timestamp","is_public","likes"])
        user_saved = df_saved[df_saved["teacher_username"]==teacher["username"]]
        if not user_saved.empty:
            for i, row in user_saved.iterrows():
                st.markdown(f"**{row['resource_name']}** ({row['type']}) - Public: {row['is_public']}")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("Delete", key=f"del_{i}"):
                        df_saved = df_saved.drop(row.name)
                        df_saved.to_csv(SAVED_RESOURCES_DB, index=False)
                        st.success(f"Deleted {row['resource_name']}")
                        st.experimental_rerun()
                with col2:
                    new_name = st.text_input(f"Rename {row['resource_name']}", value=row['resource_name'], key=f"rename_{i}")
                    if st.button("Update Name", key=f"update_{i}"):
                        df_saved.at[row.name,"resource_name"] = new_name
                        df_saved.to_csv(SAVED_RESOURCES_DB, index=False)
                        st.success(f"Updated name to {new_name}")
                        st.experimental_rerun()
                with col3:
                    is_public = st.checkbox("Public", value=row['is_public'], key=f"pub_{i}")
                    if is_public != row['is_public']:
                        df_saved.at[row.name,"is_public"] = is_public
                        df_saved.to_csv(SAVED_RESOURCES_DB, index=False)
                        st.success(f"Updated public status for {row['resource_name']}")
                        st.experimental_rerun()
        else:
            st.info("No saved resources yet")
    else:
        st.info("Log in to view your profile")

# -------------------------
# Footer
# -------------------------
st.sidebar.markdown("Developed by Prince Edward Paul © 2026")