import streamlit as st
import google.generativeai as genai
from docx import Document
from pptx import Presentation
from pptx.util import Pt
import re
import os
import random
from PIL import Image, ImageDraw, ImageFont
import io
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import time

# -------------------------
# Load environment variables
# -------------------------
load_dotenv()
gemini_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

# -------------------------
# Streamlit Page Setup
# -------------------------
st.set_page_config(page_title="AI Teacher Resource Finder", page_icon="🎓", layout="wide")

if "requests_today" not in st.session_state:
    st.session_state.requests_today = 0
if "last_request" not in st.session_state:
    st.session_state.last_request = 0

# -------------------------
# Folder Setup
# -------------------------
TEMPLATE_DIR = "templates"
PREVIEW_DIR = "template_previews"
DOWNLOAD_LOG = "downloads.csv"

os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(PREVIEW_DIR, exist_ok=True)
available_templates = [f for f in os.listdir(TEMPLATE_DIR) if f.endswith(".pptx")]

# -------------------------
# Helper Functions
# -------------------------
def sanitize_filename(name):
    return re.sub(r"[^\w\s-]", "", name).replace(" ","_")

def create_card_preview(text, color="#4B8BBE"):
    img = Image.new("RGB", (400,250), color)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except:
        font = ImageFont.load_default()
    text = text.replace("_"," ").title()
    bbox = draw.textbbox((0,0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text(((400-w)/2,(250-h)/2), text, fill="white", font=font)
    return img

def log_download(resource_name, user="anonymous"):
    row = pd.DataFrame([[resource_name, user, datetime.now()]], columns=["Resource","User","Timestamp"])
    if os.path.exists(DOWNLOAD_LOG):
        row.to_csv(DOWNLOAD_LOG, mode="a", header=False, index=False)
    else:
        row.to_csv(DOWNLOAD_LOG, index=False)

@st.cache_data
def generate_lesson(prompt, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    return response.text

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
<p style="font-size:18px;">
Create lesson plans and PowerPoint slides instantly using AI
</p>
</div>
""", unsafe_allow_html=True)

# -------------------------
# HOME PAGE
# -------------------------
if menu == "Home":
    st.subheader("🔍 Search Templates")
    search_query = st.text_input("Search template", "")
    filtered_templates = [t for t in available_templates if search_query.lower() in t.lower()] if search_query else available_templates
    if search_query and not filtered_templates:
        st.info("No templates matched your search")

    st.subheader("🎨 Choose a Slide Template")
    cols = st.columns(3)
    for i, template_file in enumerate(filtered_templates + ["🎲 Random Template"]):
        col = cols[i % 3]
        base_name = os.path.splitext(template_file)[0]
        preview_path = os.path.join(PREVIEW_DIR, f"{base_name}.png")
        with col:
            if os.path.exists(preview_path):
                st.image(preview_path, use_container_width=True)
            else:
                img = create_card_preview(base_name)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                st.image(buf.getvalue(), use_container_width=True)
            if st.button(f"Select {base_name}", key=f"btn_{i}"):
                st.session_state["chosen_template"] = template_file
                st.success(f"Selected {base_name}")

    chosen_template = st.session_state.get("chosen_template", None)
    topic = st.text_input("📘 Lesson Topic")

    if st.button("✨ Generate Lesson"):
        # --- COOLDOWN ---
        if time.time() - st.session_state.last_request < 10:
            st.warning("Please wait 10 seconds before generating another lesson.")
            st.stop()
        st.session_state.last_request = time.time()

        # --- DAILY LIMIT ---
        if st.session_state.requests_today >= 5:
            st.warning("⚠️ Daily generation limit reached (5 lessons per session).")
            st.stop()
        st.session_state.requests_today += 1

        if not topic:
            st.warning("Enter lesson topic")
        elif not chosen_template:
            st.warning("Select template first")
        elif not gemini_key:
            st.error("Gemini API key missing")
        else:
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
                # --- RETRY & QUOTA HANDLING ---
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        lesson_text = generate_lesson(prompt, gemini_key)
                        break
                    except Exception as e:
                        err_str = str(e)
                        if "ResourceExhausted" in err_str:
                            if attempt < max_retries - 1:
                                st.info("AI server busy, retrying...")
                                time.sleep(5)
                            else:
                                st.error("⚠️ AI server busy. Try again later.")
                                st.stop()
                        elif "Quota exceeded" in err_str or "429" in err_str:
                            st.error("""
⚠️ Your Gemini API quota has been exceeded.  

- Free Tier requests left: 0  
- Either wait for daily reset or upgrade your billing plan:  
[Gemini API Quotas & Limits](https://ai.google.dev/gemini-api/docs/rate-limits)
""")
                            st.stop()
                        else:
                            st.error(f"Error: {e}")
                            st.stop()

                # --- SAVE FILES ---
                safe_topic = sanitize_filename(topic)
                word_file = f"{safe_topic}_lesson.docx"
                ppt_file = f"{safe_topic}_slides.pptx"

                # Word
                doc = Document()
                doc.add_heading(f"Lesson Plan: {topic}", level=1)
                doc.add_paragraph(lesson_text)
                doc.save(word_file)

                # PPT
                template_to_use = chosen_template
                if chosen_template == "🎲 Random Template":
                    template_to_use = random.choice(available_templates)
                    st.info(f"Random template selected: {template_to_use}")

                prs = Presentation(os.path.join(TEMPLATE_DIR, template_to_use))
                slide_outline_match = re.search(r"Slide Outline:(.*)", lesson_text, re.DOTALL)
                if slide_outline_match:
                    sections = [s.strip() for s in slide_outline_match.group(1).split("\n") if s.strip()]
                else:
                    sections = [s.strip() for s in lesson_text.split("\n\n") if s.strip()]

                for section in sections:
                    if not section:
                        continue
                    slide = prs.slides.add_slide(prs.slide_layouts[1])
                    lines = section.split("\n")
                    slide.shapes.title.text = lines[0]
                    if len(lines) > 1:
                        slide.placeholders[1].text = "\n".join(lines[1:])
                prs.save(ppt_file)

                # --- DOWNLOAD BUTTONS ---
                col1, col2 = st.columns(2)
                with col1:
                    with open(word_file,"rb") as f:
                        if st.download_button("📄 Download Word", f, file_name=word_file):
                            log_download(word_file)
                with col2:
                    with open(ppt_file,"rb") as f:
                        if st.download_button("🎞️ Download Slides", f, file_name=ppt_file):
                            log_download(ppt_file)

# -------------------------
# ANALYTICS PAGE
# -------------------------
if menu == "Download Analytics":
    st.subheader("📊 Resource Downloads")
    if os.path.exists(DOWNLOAD_LOG):
        df = pd.read_csv(DOWNLOAD_LOG)
        st.dataframe(df)
        st.bar_chart(df["Resource"].value_counts())
    else:
        st.info("No downloads yet")

# -------------------------
# SETTINGS PAGE
# -------------------------
if menu == "Settings":
    st.subheader("Teacher Login & Marketplace (Coming Soon)")
    st.info("""
Future features:

• Teacher accounts
• Saved resources
• Resource marketplace
• Community templates
""")

# -------------------------
# Footer
# -------------------------
st.sidebar.markdown("Developed by Prince Edward Paul © 2026")