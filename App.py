import google.generativeai as genai
import streamlit as st
from docx import Document
from pptx import Presentation
from pptx.util import Pt
import re
import os

# --- Streamlit UI ---
st.set_page_config(page_title="AI Teacher Resource Finder", page_icon="🧠", layout="wide")
st.title("🧠 AI Teacher Resource Finder")
st.write("Instantly generate lesson notes, teaching slides, and ideas for any topic!")

# --- Gemini API Key ---
api_key = st.text_input("🔑 Enter your Gemini API Key:", type="password")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("models/gemini-2.5-flash")

    topic = st.text_input("Enter your lesson topic:")

    if st.button("Find Resources"):
        if topic.strip():
            with st.spinner("🧠 Generating your teaching pack... please wait..."):
                try:
                    prompt = f"""
                    You are an expert teacher and PowerPoint creator.
                    Create a detailed lesson pack on the topic: "{topic}".
                    Include these clear sections:

                    1. Lesson Objectives
                    2. Introduction / Starter Activity
                    3. Key Teaching Points
                    4. Guided Practice or Activities
                    5. Assessment Ideas
                    6. Summary / Conclusion
                    7. PowerPoint Slide Outline (slide titles with bullet points)
                    """

                    response = model.generate_content(prompt)
                    lesson_text = response.text

                    st.success("✅ Lesson materials generated successfully!")
                    st.write(lesson_text)

                    # --- Word document creation ---
                    doc = Document()
                    doc.add_heading(f"Lesson Plan: {topic}", level=1)
                    doc.add_paragraph(lesson_text)
                    word_file = f"{topic}_lesson.docx"
                    doc.save(word_file)

                    with open(word_file, "rb") as file:
                        st.download_button(
                            label="📄 Download Lesson as Word File",
                            data=file,
                            file_name=word_file,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )

                    # --- PowerPoint creation using template ---
                    template_path = "template.pptx"
                    if not os.path.exists(template_path):
                        st.error("⚠️ Template file not found! Please add template.pptx in your app folder.")
                    else:
                        prs = Presentation(template_path)

                        # Add title slide
                        title_slide_layout = prs.slide_layouts[0]
                        slide = prs.slides.add_slide(title_slide_layout)
                        slide.shapes.title.text = f"Lesson on {topic}"
                        if len(slide.placeholders) > 1:
                            slide.placeholders[1].text = "AI-Generated Teaching Slides"

                        # Split sections
                        sections = re.split(r'\n\d+\.\s', lesson_text)
                        sections = [s.strip() for s in sections if len(s.strip()) > 0]

                        # Add each section as a new slide
                        for section in sections:
                            slide_layout = prs.slide_layouts[1]  # Title + content layout
                            slide = prs.slides.add_slide(slide_layout)
                            lines = section.split("\n")
                            slide_title = lines[0][:80]
                            slide_content = "\n".join(lines[1:]) if len(lines) > 1 else ""

                            slide.shapes.title.text = slide_title
                            slide.placeholders[1].text = slide_content.strip()

                            # Optional font styling
                            for shape in slide.shapes:
                                if hasattr(shape, "text_frame") and shape.text_frame:
                                    for paragraph in shape.text_frame.paragraphs:
                                        for run in paragraph.runs:
                                            run.font.size = Pt(20)

                        ppt_file = f"{topic}_slides.pptx"
                        prs.save(ppt_file)

                        with open(ppt_file, "rb") as ppt:
                            st.download_button(
                                label="🎞️ Download PowerPoint Slides",
                                data=ppt,
                                file_name=ppt_file,
                                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                            )

                except Exception as e:
                    st.error(f"⚠️ An error occurred: {e}")
        else:
            st.warning("Please enter a topic before searching.")
else:
    st.info("Please enter your Gemini API key to start.")
