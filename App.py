# app.py
import streamlit as st
import os, io, time, random
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

# Modular imports
from auth import login_teacher, register_teacher, hash_password
from database import init_db, get_saved_resources, get_public_resources, save_resource_for_teacher, log_download, like_resource, get_downloads, get_notifications, mark_notifications_read
from ai_generator import generate_lesson
from ppt_generator import generate_presentation
from doc_generator import generate_doc

# -------------------------
# Constants & Folders
# -------------------------
TEMPLATE_DIR = "templates"
PREVIEW_DIR = "template_previews"
os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(PREVIEW_DIR, exist_ok=True)
available_templates = [f for f in os.listdir(TEMPLATE_DIR) if f.endswith(".pptx")]

# -------------------------
# Database init
# -------------------------
init_db()

# -------------------------
# Helper functions
# -------------------------
def sanitize_filename(name):
    return ''.join(c if c.isalnum() else '_' for c in name)

def create_card_preview(text, color="#4B8BBE"):
    img = Image.new("RGB", (400, 250), color)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except:
        font = ImageFont.load_default()
    text = text.replace("_", " ").title()
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text(((400-w)/2, (250-h)/2), text, fill="white", font=font)
    return img

# -------------------------
# Session state init
# -------------------------
for key in ["requests_today", "last_request", "logged_in_teacher", "login_prompt", "chosen_template"]:
    if key not in st.session_state:
        st.session_state[key] = 0 if key in ["requests_today", "last_request"] else None

# -------------------------
# Streamlit Page Setup
# -------------------------
st.set_page_config(page_title="AI Teacher Resource Finder", page_icon="🎓", layout="wide")

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

    filtered_templates = [t for t in available_templates if search_query.lower() in t.lower()] if search_query else available_templates
    community_df = get_public_resources(search_query, selected_category)
    resources_to_show = filtered_templates + community_df["resource_name"].tolist() + ["🎲 Random Template"]

    cols = st.columns(3)
    for i, resource in enumerate(resources_to_show):
        col = cols[i % 3]
        with col:
            preview_file = f"{sanitize_filename(resource)}.png"
            preview_path = os.path.join(PREVIEW_DIR, preview_file)
            if os.path.exists(preview_path):
                st.image(preview_path, use_container_width=True)
            else:
                img = create_card_preview(resource)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                st.image(buf.getvalue(), use_container_width=True)
            
            st.markdown(f"**{resource}**")
            row = community_df[community_df["resource_name"]==resource]
            if not row.empty:
                st.markdown(f"Likes: {row.iloc[0]['likes']}")
            if st.session_state.get("logged_in_teacher"):
                if st.button(f"Select {resource}", key=f"btn_{i}"):
                    st.session_state["chosen_template"] = resource
                if not row.empty:
                    if st.button("👍 Like", key=f"like_{i}"):
                        like_resource(int(row.iloc[0]["id"]))
                        st.success(f"You liked {resource}")
                        st.experimental_rerun()
            else:
                if st.button(f"Preview / Request Download", key=f"guest_{i}"):
                    st.info("Log in to download or generate lessons")

# -------------------------
# Teacher Section: Generate Lessons
# -------------------------
    if st.session_state.get("logged_in_teacher"):
        chosen_template = st.session_state.get("chosen_template", None)
        topic = st.text_input("📘 Lesson Topic")
        teacher = st.session_state["logged_in_teacher"]

        st.markdown("### 📊 Your Analytics")
        user_saved = get_saved_resources(teacher["username"])
        downloads_user = get_downloads().merge(user_saved, left_on="resource_name", right_on="resource_name", how="inner")
        total_generated = len(user_saved)
        total_downloads = len(downloads_user)
        most_used_template = user_saved['resource_name'].value_counts().idxmax() if not user_saved.empty else "N/A"
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Lessons Generated", total_generated)
        col2.metric("Total Downloads of Your Resources", total_downloads)
        col3.metric("Most Used Template", most_used_template)

        # Generate Lesson
        with st.form("generate_form"):
            is_public = st.checkbox("🌐 Share this lesson publicly?", value=False)
            category = st.selectbox("Category", ["General","Math","Science","English","History","Art"])
            tags = st.text_input("Tags (comma separated)", "")
            submitted = st.form_submit_button("✨ Generate Lesson")

        if submitted:
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

            # Generate AI lesson
            with st.spinner("Generating lesson..."):
                lesson_text = generate_lesson(topic)
                if not lesson_text:
                    st.stop()

            # Save Word document
            word_file = generate_doc(topic, lesson_text)
            # Save PPT presentation
            template_to_use = chosen_template if chosen_template != "🎲 Random Template" else random.choice(available_templates)
            ppt_file = generate_presentation(topic, lesson_text, template_to_use)

            # Download buttons
            col1, col2 = st.columns(2)
            with col1:
                with open(word_file,"rb") as f:
                    if st.download_button("📄 Download Word", f, file_name=os.path.basename(word_file)):
                        log_download(os.path.basename(word_file), teacher["username"])
                        save_resource_for_teacher(teacher["username"], os.path.basename(word_file), "Word", os.path.abspath(word_file), is_public, category, tags)
            with col2:
                with open(ppt_file,"rb") as f:
                    if st.download_button("🎞️ Download Slides", f, file_name=os.path.basename(ppt_file)):
                        log_download(os.path.basename(ppt_file), teacher["username"])
                        save_resource_for_teacher(teacher["username"], os.path.basename(ppt_file), "PPT", os.path.abspath(ppt_file), is_public, category, tags)

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
# Notifications / Alerts
# -------------------------
if menu=="Notifications":
    if st.session_state.get("logged_in_teacher"):
        teacher = st.session_state["logged_in_teacher"]
        st.subheader("🔔 Notifications")
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
# Settings: Login / Register / Profile
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
        teacher = st.session_state["logged_in_teacher"]
        st.markdown(f"**Username:** {teacher['username']}")
        st.markdown(f"**Email:** {teacher['email']}")

        # Password change
        st.markdown("### 🔑 Change Password")
        current_pass = st.text_input("Current Password", type="password", key="current_pass")
        new_pass = st.text_input("New Password", type="password", key="new_pass")
        confirm_pass = st.text_input("Confirm New Password", type="password", key="confirm_pass")
        if st.button("Update Password"):
            if not new_pass:
                st.error("New password cannot be empty")
            else:
                st.success("Password updated (DB update code here)")

# -------------------------
# Footer
# -------------------------
st.sidebar.markdown("Developed by Prince Edward Paul © 2026")