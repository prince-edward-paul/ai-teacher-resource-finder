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

# -------------------------
# Load environment variables
# -------------------------
load_dotenv()

try:
    gemini_key = os.environ.get("GEMINI_API_KEY") or st.secrets["GEMINI_API_KEY"]
except:
    gemini_key = None

# -------------------------
# Streamlit Page Setup
# -------------------------
st.set_page_config(
    page_title="AI Teacher Resource Finder",
    page_icon="🎓",
    layout="wide"
)

# -------------------------
# Sidebar Navigation
# -------------------------
st.sidebar.title("Navigation")
menu = st.sidebar.radio(
    "Menu",
    ["Home", "Download Analytics", "Settings"]
)

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
margin-bottom:20px;
">
<h1>🎓 AI Teacher Resource Finder</h1>
<p style="font-size:18px;">
Create lesson plans and PowerPoint slides instantly using AI
</p>
</div>
""", unsafe_allow_html=True)

# -------------------------
# Folder Setup
# -------------------------
TEMPLATE_DIR = "templates"
PREVIEW_DIR = "template_previews"
DOWNLOAD_LOG = "downloads.csv"

os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(PREVIEW_DIR, exist_ok=True)

available_templates = [
    f for f in os.listdir(TEMPLATE_DIR)
    if f.endswith(".pptx")
]

# -------------------------
# Helper Functions
# -------------------------

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

    draw.text(
        ((400-w)/2,(250-h)/2),
        text,
        fill="white",
        font=font
    )

    return img


def log_download(resource_name, user="anonymous"):

    row = pd.DataFrame(
        [[resource_name,user,datetime.now()]],
        columns=["Resource","User","Timestamp"]
    )

    if os.path.exists(DOWNLOAD_LOG):

        row.to_csv(
            DOWNLOAD_LOG,
            mode="a",
            header=False,
            index=False
        )

    else:

        row.to_csv(
            DOWNLOAD_LOG,
            index=False
        )


# -------------------------
# HOME PAGE
# -------------------------

if menu == "Home":

    if not available_templates:
        st.warning("⚠️ No templates found in the templates folder.")
        st.stop()

    st.subheader("🔍 Search for templates")

    search_query = st.text_input("Search template")

    if search_query:

        filtered_templates = [
            t for t in available_templates
            if search_query.lower() in t.lower()
        ]

    else:

        filtered_templates = available_templates

    if search_query and not filtered_templates:
        st.info("No templates matched your search")

    template_options = filtered_templates + ["🎲 Random Template"]

    st.subheader("🎨 Choose a Slide Template")

    cols = st.columns(3)

    for i, template_file in enumerate(template_options):

        col = cols[i % 3]

        base_name = os.path.splitext(template_file)[0]

        preview_path = os.path.join(
            PREVIEW_DIR,
            f"{base_name}.png"
        )

        with col:

            if os.path.exists(preview_path):

                st.image(
                    preview_path,
                    use_container_width=True
                )

            else:

                img = create_card_preview(base_name)

                buf = io.BytesIO()

                img.save(buf, format="PNG")

                st.image(
                    buf.getvalue(),
                    use_container_width=True
                )

            if st.button(
                f"Select {base_name}",
                key=f"btn_{i}"
            ):

                st.session_state["chosen_template"] = template_file

                st.success(f"Selected {base_name}")

    chosen_template = st.session_state.get(
        "chosen_template",
        None
    )

    topic = st.text_input("📘 Lesson Topic")

    if st.button("✨ Generate Lesson"):

        if not topic:

            st.warning("Enter lesson topic")

        elif not chosen_template:

            st.warning("Select template first")

        elif not gemini_key:

            st.error("Gemini API key missing")

        else:

            with st.spinner("Generating lesson..."):

                genai.configure(api_key=gemini_key)

                model = genai.GenerativeModel("gemini-2.0-flash")

                prompt = f"""
Create a structured lesson plan for: {topic}

Include:

1. Lesson Objectives
2. Introduction
3. Key Teaching Points
4. Activities
5. Assessment
6. Summary
7. PowerPoint slide outline
"""

                response = model.generate_content(prompt)

                lesson_text = response.text

                st.success("Lesson Generated")

                # ------------------
                # Save Word File
                # ------------------

                doc = Document()

                doc.add_heading(
                    f"Lesson Plan: {topic}",
                    level=1
                )

                doc.add_paragraph(lesson_text)

                word_file = f"{topic}_lesson.docx"

                doc.save(word_file)

                # ------------------
                # Save PowerPoint
                # ------------------

                if chosen_template == "🎲 Random Template":

                    chosen_template = random.choice(
                        available_templates
                    )

                template_path = os.path.join(
                    TEMPLATE_DIR,
                    chosen_template
                )

                prs = Presentation(template_path)

                sections = re.split(
                    r"\n\d+\.\s",
                    lesson_text
                )

                sections = [
                    s.strip()
                    for s in sections
                    if s.strip()
                ]

                for section in sections:

                    slide = prs.slides.add_slide(
                        prs.slide_layouts[1]
                    )

                    lines = section.split("\n")

                    title = lines[0]

                    body = "\n".join(lines[1:])

                    slide.shapes.title.text = title

                    slide.placeholders[1].text = body

                ppt_file = f"{topic}_slides.pptx"

                prs.save(ppt_file)

                # ------------------
                # Downloads
                # ------------------

                col1,col2 = st.columns(2)

                with col1:

                    if st.download_button(
                        "📄 Download Word",
                        data=open(word_file,"rb"),
                        file_name=word_file
                    ):

                        log_download(word_file)

                with col2:

                    if st.download_button(
                        "📊 Download Slides",
                        data=open(ppt_file,"rb"),
                        file_name=ppt_file
                    ):

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

    st.subheader("Teacher Login (Coming Soon)")

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

st.sidebar.markdown(
"Developed by Prince Edward Paul © 2026"
)