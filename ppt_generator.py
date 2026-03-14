# ppt_generator.py
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE
import os
import uuid
import re
import requests
from io import BytesIO
from PIL import Image

def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)

def generate_presentation(topic, lesson_text, template_file):
    """
    Generates a PowerPoint presentation based on a lesson text.
    - Follows slide-by-slide outline in the lesson text.
    - Inserts suggested images if mentioned in the outline.
    - Student-centered, 21st-century teaching format.
    Returns the path to the generated PPTX file.
    """
    prs = Presentation(os.path.join("templates", template_file))

    # Split lesson into sections for slides
    sections = [s.strip() for s in lesson_text.split("\n\n") if s.strip()]

    for section in sections:
        lines = section.split("\n")
        slide_title = lines[0]  # First line is the title
        content_lines = lines[1:]  # Remaining lines are content

        # Use Title + Content layout if available
        slide_layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]
        slide = prs.slides.add_slide(slide_layout)
        slide.shapes.title.text = slide_title

        # Insert content in the placeholder or create a textbox
        if len(slide.placeholders) > 1:
            slide.placeholders[1].text = "\n".join(content_lines)
        else:
            left, top, width, height = Inches(1), Inches(1.5), Inches(8), Inches(4)
            txBox = slide.shapes.add_textbox(left, top, width, height)
            tf = txBox.text_frame
            tf.text = "\n".join(content_lines)
            for paragraph in tf.paragraphs:
                paragraph.font.size = Pt(18)

        # Check for suggested images in the content (e.g., "Image: https://...")
        for line in content_lines:
            if "Image:" in line or "Source:" in line:
                url_match = re.search(r"(https?://\S+)", line)
                if url_match:
                    url = url_match.group(1)
                    try:
                        response = requests.get(url)
                        img_stream = BytesIO(response.content)
                        # Add image to slide
                        slide.shapes.add_picture(img_stream, Inches(1), Inches(3), width=Inches(6))
                    except:
                        pass  # ignore image errors

    # Save generated presentation
    os.makedirs("generated", exist_ok=True)
    file_name = f"{sanitize_filename(topic)}_{uuid.uuid4().hex[:5]}.pptx"
    path = os.path.join("generated", file_name)
    prs.save(path)
    return path