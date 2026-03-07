import streamlit as st
import google.generativeai as genai
from docx import Document
from pptx import Presentation
from pptx.util import Pt
import re
import os
import random
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import io

# --- Load environment variables ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# --- Streamlit Page Setup ---
st.set_page_config(page_title="AI Teacher Resource Finder", page_icon="🧠", layout="wide")
st.title("🧠 AI Teacher Resource Finder")
st.caption("Create beautiful, ready-to-teach lesson slides with AI in seconds!")

import os

# Get key from Streamlit Secrets
gemini_key = os.environ.get("GEMINI_API_KEY")

# --- Folder Setup ---
TEMPLATE_DIR = "templates"
PREVIEW_DIR = "template_previews"

# Ensure folders exist
if not os.path.exists(TEMPLATE_DIR):
    os.makedirs(TEMPLATE_DIR)
if not os.path.exists(PREVIEW_DIR):
    os.makedirs(PREVIEW_DIR)

# --- Load Templates ---
available_templates = [f for f in os.listdir(TEMPLATE_DIR) if f.endswith(".pptx")]

if not available_templates:
    st.error("⚠️ No PowerPoint templates found in the 'templates' folder. Please add at least one .pptx file.")
    st.stop()

# --- Template Selection Section ---
st.subheader("🎨 Choose a Slide Template")

cols = st.columns(3)
chosen_template = st.session_state.get("chosen_template", None)
template_options = available_templates + ["🎲 Random Template"]

def create_placeholder_preview(text, color):
    """Create a simple colored preview image when no PNG preview exists."""
    img = Image.new("RGB", (400, 250), color)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    text = text.replace("_", " ").title()
    w, h = draw.textsize(text, font=font)
    draw.text(((400 - w) / 2, (250 - h) / 2), text, fill="white", font=font)
    return img

placeholder_colors = [
    "#4B8BBE", "#306998", "#FFD43B", "#FFE873", "#646464",
    "#FF5733", "#33FF57", "#339BFF", "#8E44AD", "#2ECC71"
]

for i, template_file in enumerate(template_options):
    col = cols[i % 3]
    base_name = os.path.splitext(template_file)[0]
    preview_path = os.path.join(PREVIEW_DIR, f"{base_name}.png")

    with col:
        if os.path.exists(preview_path):
            st.image(preview_path, use_container_width=True)
        else:
            color = placeholder_colors[i % len(placeholder_colors)]
            img = create_placeholder_preview(base_name, color)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            st.image(buf.getvalue(), use_container_width=True)

        if st.button(f"Select: {base_name.replace('_', ' ').title()}"):
            st.session_state["chosen_template"] = template_file
            chosen_template = template_file
            st.success(f"✅ Selected: {base_name.title()}")

# --- Get Selected Template ---
chosen_template = st.session_state.get("chosen_template", None)

# --- Main Lesson Generator ---
if api_key_input:
    genai.configure(api_key=api_key_input)
    model = genai.GenerativeModel("models/gemini-2.0-flash")

    topic = st.text_input("📘 Enter your lesson topic:")

    if st.button("✨ Generate Lesson Slides"):
        if not topic.strip():
            st.warning("Please enter a topic before generating.")
        elif not chosen_template:
            st.warning("Please select a slide template first.")
        else:
            with st.spinner("🧠 Generating your teaching pack... please wait..."):
                try:
                    prompt = f"""
                    You are an expert teacher and PowerPoint creator.
                    Create a detailed lesson pack on the topic: "{topic}".
                    Include these sections clearly labeled:

                    1. Lesson Objectives
                    2. Introduction / Starter Activity
                    3. Key Teaching Points
                    4. Guided Practice / Class Activities
                    5. Assessment Ideas
                    6. Summary / Conclusion
                    7. PowerPoint Slide Outline (titles + bullet points)

                    Make it engaging and age-appropriate.
                    """

                    # --- Generate Lesson Text ---
                    response = model.generate_content(prompt)
                    lesson_text = response.text

                    st.success("✅ Lesson materials generated successfully!")
                    st.text_area("📄 Generated Lesson Content:", lesson_text, height=300)

                    # --- Save Word File ---
                    doc = Document()
                    doc.add_heading(f"Lesson Plan: {topic}", level=1)
                    doc.add_paragraph(lesson_text)
                    word_file = f"{topic}_lesson.docx"
                    doc.save(word_file)

                    with open(word_file, "rb") as file:
                        st.download_button(
                            label="📄 Download Lesson (Word)",
                            data=file,
                            file_name=word_file,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )

                    # --- Handle Random Template ---
                    if chosen_template == "🎲 Random Template":
                        chosen_template = random.choice(available_templates)

                    # --- Load Template ---
                    template_path = os.path.join(TEMPLATE_DIR, chosen_template)
                    prs = Presentation(template_path)

                    # --- Add Generated Slides ---
                    sections = re.split(r'\n\d+\.\s', lesson_text)
                    sections = [s.strip() for s in sections if len(s.strip()) > 0]

                    for section in sections:
                        slide = prs.slides.add_slide(prs.slide_layouts[1])
                        title_box = slide.shapes.title
                        content_box = slide.placeholders[1]

                        lines = section.split("\n")
                        title_box.text = lines[0][:80]
                        body = "\n".join(lines[1:]) if len(lines) > 1 else ""
                        content_box.text = body.strip()

                        # Adjust font size
                        for shape in slide.shapes:
                            if hasattr(shape, "text_frame") and shape.text_frame:
                                for paragraph in shape.text_frame.paragraphs:
                                    for run in paragraph.runs:
                                        run.font.size = Pt(18)

                    # --- Save PowerPoint ---
                    ppt_file = f"{topic}_slides_{os.path.splitext(chosen_template)[0]}.pptx"
                    prs.save(ppt_file)

                    with open(ppt_file, "rb") as ppt:
                        st.download_button(
                            label="🎞️ Download PowerPoint Slides",
                            data=ppt,
                            file_name=ppt_file,
                            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                        )

                except Exception as e:
                    st.error(f"⚠️ Error: {e}")
else:
    st.info("Please enter your Gemini API key to start.")

# --- Footer ---
st.sidebar.markdown("**Developed by Prince Edward Paul © 2025**")




