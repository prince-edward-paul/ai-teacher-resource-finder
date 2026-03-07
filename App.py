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

# --- Load environment variables ---
load_dotenv()
gemini_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

# --- Streamlit Page Setup ---
st.set_page_config(page_title="AI Teacher Resource Finder",
                   page_icon="🎓",
                   layout="wide")

# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
menu = st.sidebar.radio("Menu", ["Home", "Download Analytics", "Settings"])

# --- Hero Section ---
st.markdown("""
<div style="
    background: linear-gradient(135deg, #4B8BBE, #306998);
    padding: 25px;
    border-radius: 15px;
    color: white;
    text-align:center;
    margin-bottom:20px;">
    <h1>🎓 AI Teacher Resource Finder</h1>
    <p style="font-size:18px;">Create, customize, and download ready-to-teach lesson resources in seconds!</p>
</div>
""", unsafe_allow_html=True)

# --- Folder Setup ---
TEMPLATE_DIR = "templates"
PREVIEW_DIR = "template_previews"
DOWNLOAD_LOG = "downloads.csv"
os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(PREVIEW_DIR, exist_ok=True)

available_templates = [f for f in os.listdir(TEMPLATE_DIR) if f.endswith(".pptx")]
if not available_templates:
    st.error("⚠️ No PowerPoint templates found in 'templates' folder.")
    st.stop()

# --- Helper Functions ---
def create_card_preview(text, color="#4B8BBE"):
    img = Image.new("RGB", (400, 250), color)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    text = text.replace("_", " ").title()
    w, h = draw.textsize(text, font=font)
    draw.text(((400 - w)/2, (250 - h)/2), text, fill="white", font=font)
    return img

def log_download(resource_name, user="anonymous"):
    df = pd.DataFrame([[resource_name, user, datetime.now()]],
                      columns=["Resource", "User", "Timestamp"])
    if os.path.exists(DOWNLOAD_LOG):
        df.to_csv(DOWNLOAD_LOG, mode="a", header=False, index=False)
    else:
        df.to_csv(DOWNLOAD_LOG, index=False)

# --- Home Page ---
if menu == "Home":
    st.subheader("🔍 Search & Generate Lessons")
    
    search_query = st.text_input("Search for a resource:")
    filtered_templates = [t for t in available_templates if search_query.lower() in t.lower()] if search_query else available_templates
    if search_query and not filtered_templates:
        st.info("No templates matched your search.")

    st.subheader("🎨 Choose a Slide Template")
    template_options = filtered_templates + ["🎲 Random Template"]
    cols = st.columns(3)
    gradient_colors = [
        "linear-gradient(135deg, #4B8BBE, #306998)",
        "linear-gradient(135deg, #FFD43B, #FFE873)",
        "linear-gradient(135deg, #FF5733, #FF8D33)",
        "linear-gradient(135deg, #33FF57, #33FFBD)",
        "linear-gradient(135deg, #8E44AD, #9B59B6)"
    ]

    for i, template_file in enumerate(template_options):
        col = cols[i % 3]
        base_name = os.path.splitext(template_file)[0]
        preview_path = os.path.join(PREVIEW_DIR, f"{base_name}.png")
        gradient = gradient_colors[i % len(gradient_colors)]

        with col:
            # Show preview image or placeholder
            if os.path.exists(preview_path):
                st.image(preview_path, use_container_width=True)
            else:
                img = create_card_preview(base_name, "#4B8BBE")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                st.image(buf.getvalue(), use_container_width=True)

            # Card-style with gradient and hover effect
            st.markdown(f"""
            <div style="
                background: {gradient};
                padding:15px;
                border-radius:12px;
                text-align:center;
                color:white;
                font-weight:bold;
                font-family: sans-serif;
                box-shadow: 3px 3px 10px rgba(0,0,0,0.2);
                transition: transform 0.2s, box-shadow 0.2s;
                margin-bottom:10px;
            " onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='5px 5px 15px rgba(0,0,0,0.4)';" 
               onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='3px 3px 10px rgba(0,0,0,0.2)';">
                {base_name.replace('_',' ').title()}
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Select: {base_name.replace('_',' ').title()}"):
                st.session_state["chosen_template"] = template_file
                st.success(f"✅ Selected: {base_name.title()}")

    chosen_template = st.session_state.get("chosen_template", None)
    topic = st.text_input("📘 Enter your lesson topic:")

    generate_btn = st.button("✨ Generate Lesson Slides")
    if generate_btn:
        if not topic.strip():
            st.warning("Please enter a topic before generating.")
        elif not chosen_template:
            st.warning("Please select a slide template first.")
        else:
            with st.spinner("🧠 Generating your teaching pack..."):
                try:
                    genai.configure(api_key=gemini_key)
                    model = genai.GenerativeModel("models/gemini-2.0-flash")
                    prompt = f"""
                    You are an expert teacher and PowerPoint creator.
                    Create a detailed lesson pack on the topic: "{topic}".
                    Include sections:
                    1. Lesson Objectives
                    2. Introduction / Starter Activity
                    3. Key Teaching Points
                    4. Guided Practice / Class Activities
                    5. Assessment Ideas
                    6. Summary / Conclusion
                    7. PowerPoint Slide Outline
                    """
                    response = model.generate_content(prompt)
                    lesson_text = response.text
                    st.success("✅ Lesson generated!")

                    # --- Save Word ---
                    doc = Document()
                    doc.add_heading(f"Lesson Plan: {topic}", level=1)
                    doc.add_paragraph(lesson_text)
                    word_file = f"{topic}_lesson.docx"
                    doc.save(word_file)

                    # --- Save PowerPoint ---
                    if chosen_template == "🎲 Random Template":
                        chosen_template = random.choice(available_templates)
                    template_path = os.path.join(TEMPLATE_DIR, chosen_template)
                    prs = Presentation(template_path)

                    sections = re.split(r'\n\d+\.\s', lesson_text)
                    sections = [s.strip() for s in sections if s.strip()]
                    for section in sections:
                        slide = prs.slides.add_slide(prs.slide_layouts[1])
                        title_box = slide.shapes.title
                        content_box = slide.placeholders[1]
                        lines = section.split("\n")
                        title_box.text = lines[0][:80]
                        body = "\n".join(lines[1:]) if len(lines) > 1 else ""
                        content_box.text = body.strip()
                        for shape in slide.shapes:
                            if hasattr(shape, "text_frame") and shape.text_frame:
                                for paragraph in shape.text_frame.paragraphs:
                                    for run in paragraph.runs:
                                        run.font.size = Pt(18)

                    ppt_file = f"{topic}_slides_{os.path.splitext(chosen_template)[0]}.pptx"
                    prs.save(ppt_file)

                    # --- Download Buttons with Gradient ---
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.download_button(
                            label="📄 Download Word Lesson",
                            data=open(word_file, "rb"),
                            file_name=word_file,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key="download_word"
                        ):
                            log_download(word_file)
                    with col2:
                        if st.download_button(
                            label="🎞️ Download PowerPoint Slides",
                            data=open(ppt_file, "rb"),
                            file_name=ppt_file,
                            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                            key="download_ppt"
                        ):
                            log_download(ppt_file)

                except Exception as e:
                    st.error(f"⚠️ Error: {e}")

# --- Download Analytics Page ---
if menu == "Download Analytics":
    st.subheader("📊 Download Analytics")
    if os.path.exists(DOWNLOAD_LOG):
        df = pd.read_csv(DOWNLOAD_LOG)
        st.dataframe(df)
        st.bar_chart(df['Resource'].value_counts())
    else:
        st.info("No downloads logged yet.")

# --- Settings / Teacher Login Placeholder ---
if menu == "Settings":
    st.subheader("⚙️ Settings / Teacher Login")
    st.info("Feature under development: teacher login and personalized dashboard.")

# --- Footer ---
st.sidebar.markdown("**Developed by Prince Edward Paul © 2026**")