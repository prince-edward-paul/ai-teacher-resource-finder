import streamlit as st
import os
import io
import random
import time
from PIL import Image, ImageDraw, ImageFont

# Import our modular files
from auth import login_teacher, register_teacher, hash_password
from database import init_db, save_resource, get_user_resources, get_public_resources, log_download, like_resource, get_notifications, mark_notifications_read, get_downloads
from ai_generator import generate_lesson
from ppt_generator import generate_presentation, TEMPLATE_DIR
from doc_generator import generate_doc

# -------------------------
# Init database
# -------------------------
init_db()

# -------------------------
# Session State
# -------------------------
for key in ["requests_today","last_request","logged_in_teacher","login_prompt","chosen_template"]:
    if key not in st.session_state:
        st.session_state[key] = 0 if key in ["requests_today","last_request"] else None

# -------------------------
# Page config
# -------------------------
st.set_page_config(page_title="AI Teacher Resource Finder", page_icon="🎓", layout="wide")

# -------------------------
# Helpers
# -------------------------
def sanitize_filename(name):
    import re
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

# -------------------------
# Sidebar Navigation
# -------------------------
st.sidebar.title("Navigation")
menu = st.sidebar.radio("Menu", ["Home", "Download Analytics", "Notifications", "Settings"])

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
    categories = ["All","Math","Science","English","History","Art"]
    selected_category = st.selectbox("Category", categories)
    search_query = st.text_input("Search template/resource", "")

    # Show template previews
    templates = [f for f in os.listdir(TEMPLATE_DIR) if f.endswith(".pptx")]
    st.markdown("### 🎨 Available Templates")
    template_cols = st.columns(len(templates))
    for idx, t in enumerate(templates):
        with template_cols[idx]:
            st.image(create_card_preview(t))
            if st.button(f"Select {t}", key=f"template_{idx}"):
                st.session_state["chosen_template"] = t

    community_df = get_public_resources(search_query, selected_category)
    st.markdown("### 🌐 Community Resources")
    for i, row in community_df.iterrows():
        st.write(f"**{row['resource_name']}** (Likes: {row['likes']})")
        if st.session_state.get("logged_in_teacher"):
            if st.button(f"👍 Like", key=f"like_{i}"):
                like_resource(row["id"])
                st.success("You liked this resource")
                st.experimental_rerun()
        if st.button(f"📥 Download", key=f"download_{i}"):
            st.info("Download feature will appear after login")

# -------------------------
# Teacher Section
# -------------------------
if st.session_state.get("logged_in_teacher"):
    teacher = st.session_state["logged_in_teacher"]
    st.markdown(f"### Welcome, {teacher['username']}")

    st.subheader("✨ Generate Lesson")
    topic = st.text_input("📘 Lesson Topic")
    chosen_template = st.session_state.get("chosen_template")

    is_public = st.checkbox("🌐 Share this lesson publicly?", value=False)
    category = st.selectbox("Category", ["General","Math","Science","English","History","Art"])
    tags = st.text_input("Tags (comma separated)", "")

    if st.button("Generate Lesson"):
        current_time = time.time()
        if current_time - st.session_state.last_request < 10:
            st.warning("Please wait 10 seconds before generating another lesson.")
            st.stop()
        st.session_state.last_request = current_time
        if not topic:
            st.warning("Enter lesson topic")
            st.stop()
        if not chosen_template:
            st.warning("Select a template first")
            st.stop()

        with st.spinner("Generating lesson..."):
            lesson_text = generate_lesson(topic)
            doc_path = generate_doc(topic, lesson_text)
            ppt_path = generate_presentation(topic, lesson_text, chosen_template)

        col1, col2 = st.columns(2)
        with col1:
            with open(doc_path,"rb") as f:
                st.download_button("📄 Download Word", f, file_name=os.path.basename(doc_path))
                save_resource(teacher["username"], os.path.basename(doc_path), "Word", doc_path, is_public, category, tags)
                log_download(os.path.basename(doc_path), teacher["username"])
        with col2:
            with open(ppt_path,"rb") as f:
                st.download_button("🎞️ Download Slides", f, file_name=os.path.basename(ppt_path))
                save_resource(teacher["username"], os.path.basename(ppt_path), "PPT", ppt_path, is_public, category, tags)
                log_download(os.path.basename(ppt_path), teacher["username"])

# -------------------------
# Download Analytics
# -------------------------
if menu=="Download Analytics":
    st.subheader("📊 Resource Downloads")
    df = get_downloads()
    if not df.empty:
        st.dataframe(df)
        st.bar_chart(df["resource_name"].value_counts())
    else:
        st.info("No downloads yet")

# -------------------------
# Notifications
# -------------------------
if menu=="Notifications":
    if st.session_state.get("logged_in_teacher"):
        notifs = get_notifications(teacher["username"])
        if notifs.empty:
            st.info("No new notifications")
        else:
            for i, row in notifs.iterrows():
                st.info(f"{row['timestamp']}: {row['message']}")
            mark_notifications_read(teacher["username"])
    else:
        st.warning("Log in to view notifications")

# -------------------------
# Settings (Login/Register/Profile)
# -------------------------
tab1, tab2, tab3 = st.tabs(["Login","Register","Profile"])

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

with tab3:
    if st.session_state.get("logged_in_teacher"):
        st.markdown(f"**Username:** {teacher['username']}")
        st.markdown(f"**Email:** {teacher['email']}")

# -------------------------
# Footer
# -------------------------
st.sidebar.markdown("Developed by Prince Edward Paul © 2026")