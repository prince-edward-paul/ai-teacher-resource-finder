# doc_generator.py
from docx import Document
import os
import uuid

def generate_doc(topic, lesson_text):
    """
    Generate a Word (.docx) lesson plan file from text
    Returns the path to the saved document
    """
    doc = Document()
    doc.add_heading(f"Lesson Plan: {topic}", level=1)
    for line in lesson_text.split("\n"):
        if line.strip():  # avoid empty lines
            doc.add_paragraph(line.strip())

    os.makedirs("generated", exist_ok=True)
    file_name = f"{topic}_{uuid.uuid4().hex[:5]}.docx"
    path = os.path.join("generated", file_name)
    doc.save(path)
    return path